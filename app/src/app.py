import atexit
import csv
import io
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from threading import Lock

import pymysql
from flask import Flask, g, jsonify, render_template, request, session
from pythonjsonlogger import jsonlogger
from werkzeug.security import check_password_hash, generate_password_hash

from dotenv import load_dotenv


# Database connection pool
class ConnectionPool:
    def __init__(self, host, user, password, database, port=3306, pool_size=5):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.pool_size = pool_size
        self.connections = []
        self.lock = Lock()

    def get_connection(self):
        with self.lock:
            if self.connections:
                return self.connections.pop()
        
        try:
            conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                autocommit=False,
                cursorclass=pymysql.cursors.DictCursor
            )
            return conn
        except pymysql.Error as e:
            raise Exception(f"Failed to connect to database: {e}")

    def return_connection(self, conn):
        try:
            conn.ping()
            with self.lock:
                if len(self.connections) < self.pool_size:
                    self.connections.append(conn)
                else:
                    conn.close()
        except pymysql.Error:
            conn.close()

    def close_all(self):
        with self.lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()


pool = None


def get_db_connection():
    """Get a database connection."""
    global pool
    if pool is None:
        raise Exception("Database pool not initialized")
    return pool.get_connection()


def return_db_connection(conn):
    """Return a connection to the pool."""
    global pool
    if pool:
        pool.return_connection(conn)


def _get_db_config():
    """Get database configuration."""
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_port = int(os.getenv("DB_PORT", "3306"))
    
    if not (db_host and db_name and db_user and db_password):
        raise Exception("Database configuration incomplete. Please set DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
    
    return {
        "host": db_host,
        "user": db_user,
        "password": db_password,
        "database": db_name,
        "port": db_port,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5"))
    }


def _initialize_database(app):
    """Initialize database schema."""
    global pool
    
    config = _get_db_config()

    # Create pool
    pool = ConnectionPool(**config)
    atexit.register(lambda: pool.close_all())
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255),
            display_name VARCHAR(255) NOT NULL,
            dark_mode BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            color VARCHAR(7) DEFAULT '#3498db',
            user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description VARCHAR(1000),
            completed BOOLEAN DEFAULT FALSE,
            priority VARCHAR(10) DEFAULT 'medium',
            due_date DATETIME,
            user_id INT NOT NULL,
            category_id INT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id),
            INDEX idx_user_id (user_id),
            INDEX idx_category_id (category_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            todo_id INT NOT NULL,
            remind_at DATETIME NOT NULL,
            sent BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (todo_id) REFERENCES todos(id) ON DELETE CASCADE,
            INDEX idx_todo_id (todo_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_shares (
            id INT AUTO_INCREMENT PRIMARY KEY,
            todo_id INT NOT NULL,
            shared_with_user_id INT NOT NULL,
            can_edit BOOLEAN DEFAULT FALSE,
            shared_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (todo_id) REFERENCES todos(id) ON DELETE CASCADE,
            FOREIGN KEY (shared_with_user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_todo_id (todo_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        conn.commit()
        app.logger.info("Database schema initialized", extra={"request_id": "startup"})
    except pymysql.Error as exc:
        conn.rollback()
        app.logger.error("Failed to initialize database", extra={"request_id": "startup", "error": str(exc)})
        raise
    finally:
        return_db_connection(conn)


def _configure_logger() -> logging.Logger:
    logger = logging.getLogger("todo-app")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Module-level logger initialized once
logger = _configure_logger()


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        return_db_connection(conn)


def _current_user_id() -> int | None:
    return session.get("user_id")


def _require_auth() -> tuple | None:
    if not _current_user_id():
        return jsonify({"error": "unauthorized"}), 401
    return None


def _load_environment() -> None:
    env_file = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_file, override=False)


def create_app() -> Flask:
    _load_environment()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        hours=int(os.getenv("SESSION_TTL_HOURS", "12"))
    )
    app.logger = logger

    # Initialize database
    _initialize_database(app)

    @app.before_request
    def add_request_id() -> None:
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        session.permanent = True

    @app.after_request
    def set_request_headers(response):
        response.headers["X-Request-ID"] = g.request_id
        return response



    @app.get("/health")
    def health():
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            return jsonify({"status": "ok"}), 200
        except Exception as exc:
            app.logger.error("Health check failed", extra={"request_id": g.request_id, "error": str(exc)})
            return jsonify({"status": "degraded"}), 503

    @app.get("/")
    def landing():
        return render_template("landing.html")

    @app.get("/app")
    def index():
        return render_template("index.html")

    @app.get("/api")
    def api_info():
        return jsonify({
            "name": "Todo App",
            "version": "1.0.0",
        })

    @app.get("/auth/me")
    def auth_me():
        user_id = _current_user_id()
        if not user_id:
            return jsonify({"authenticated": False}), 200

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, display_name, dark_mode FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

        if not user:
            session.clear()
            return jsonify({"authenticated": False}), 200

        return jsonify({
            "authenticated": True,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "display_name": user["display_name"],
                "dark_mode": user["dark_mode"]
            }
        }), 200

    @app.post("/auth/signup")
    def auth_signup():
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", "")).strip()
        display_name = str(payload.get("display_name", "")).strip() or email.split("@")[0]

        if not email or not password:
            return jsonify({"error": "email and password required"}), 400

        if len(password) < 6:
            return jsonify({"error": "password must be at least 6 characters"}), 400

        password_hash = generate_password_hash(password)

        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, display_name) VALUES (%s, %s, %s)",
                    (email, password_hash, display_name)
                )
                user_id = cursor.lastrowid
            except pymysql.IntegrityError:
                return jsonify({"error": "email already registered"}), 409

            session["user_id"] = user_id

        return jsonify({"id": user_id, "email": email, "display_name": display_name}), 201

    @app.post("/auth/login")
    def auth_login():
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", "")).strip()

        if not email or not password:
            return jsonify({"error": "email and password required"}), 400

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "invalid email or password"}), 401

        session["user_id"] = user["id"]
        return jsonify({"id": user["id"], "email": email}), 200

    @app.post("/auth/logout")
    def auth_logout():
        session.clear()
        return jsonify({"authenticated": False}), 200

    @app.get("/todos")
    def list_todos():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        
        search = request.args.get("search", "").strip()
        category_id = request.args.get("category_id", type=int)
        priority = request.args.get("priority", "").strip()
        completed = request.args.get("completed", type=lambda x: x.lower() == "true")
        sort_by = request.args.get("sort_by", "created_at")
        export_format = request.args.get("export", "").strip()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM todos WHERE user_id = %s"
            params = [user_id]
            
            if search:
                query += " AND title LIKE %s"
                params.append(f"%{search}%")
            
            if category_id:
                query += " AND category_id = %s"
                params.append(category_id)
            
            if priority:
                query += " AND priority = %s"
                params.append(priority)
            
            if completed is not None:
                query += " AND completed = %s"
                params.append(completed)
            
            if sort_by == "due_date":
                query += " ORDER BY due_date ASC"
            elif sort_by == "priority":
                query += " ORDER BY FIELD(priority, 'high', 'medium', 'low')"
            else:
                query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            todos = cursor.fetchall()
        
        if export_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Title", "Priority", "Status", "Due Date"])
            for todo in todos:
                status = "Done" if todo["completed"] else "Pending"
                due_date = todo["due_date"].strftime("%Y-%m-%d") if todo["due_date"] else ""
                writer.writerow([todo["id"], todo["title"], todo["priority"], status, due_date])
            
            response = app.response_class(
                response=output.getvalue(),
                status=200,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=todos.csv"}
            )
            return response
        
        return jsonify(todos), 200

    @app.post("/todos")
    def create_todo():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        title = str(payload.get("title", "")).strip()
        if not title:
            return jsonify({"error": "title is required"}), 400

        description = str(payload.get("description", "")).strip() or None
        priority = str(payload.get("priority", "medium")).strip()
        category_id = payload.get("category_id")
        due_date = payload.get("due_date")

        if priority not in ["low", "medium", "high"]:
            priority = "medium"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO todos (title, description, priority, category_id, due_date, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (title, description, priority, category_id, due_date, user_id)
            )
            todo_id = cursor.lastrowid

            cursor.execute("SELECT * FROM todos WHERE id = %s", (todo_id,))
            todo = cursor.fetchone()

        return jsonify(todo), 201

    @app.get("/todos/<int:todo_id>")
    def get_todo(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM todos WHERE id = %s AND user_id = %s", (todo_id, user_id))
            todo = cursor.fetchone()

        if not todo:
            return jsonify({"error": "todo not found"}), 404

        return jsonify(todo), 200

    @app.patch("/todos/<int:todo_id>")
    def update_todo(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM todos WHERE id = %s AND user_id = %s", (todo_id, user_id))
            todo = cursor.fetchone()

            if not todo:
                return jsonify({"error": "todo not found"}), 404

            updates = []
            values = []

            if "title" in payload:
                title = str(payload["title"]).strip()
                if not title:
                    return jsonify({"error": "title cannot be empty"}), 400
                updates.append("title = %s")
                values.append(title)

            if "description" in payload:
                updates.append("description = %s")
                values.append(str(payload["description"]).strip() or None)

            if "completed" in payload:
                updates.append("completed = %s")
                values.append(payload["completed"])

            if "priority" in payload:
                priority = str(payload["priority"]).strip()
                if priority in ["low", "medium", "high"]:
                    updates.append("priority = %s")
                    values.append(priority)

            if "due_date" in payload:
                updates.append("due_date = %s")
                values.append(payload["due_date"])

            if "category_id" in payload:
                updates.append("category_id = %s")
                values.append(payload["category_id"])

            if not updates:
                return jsonify(todo), 200

            values.append(todo_id)
            query = f"UPDATE todos SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, values)

            cursor.execute("SELECT * FROM todos WHERE id = %s", (todo_id,))
            updated_todo = cursor.fetchone()

        return jsonify(updated_todo), 200

    @app.delete("/todos/<int:todo_id>")
    def delete_todo(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM todos WHERE id = %s AND user_id = %s", (todo_id, user_id))
            if not cursor.fetchone():
                return jsonify({"error": "todo not found"}), 404

            cursor.execute("DELETE FROM todos WHERE id = %s", (todo_id,))

        return jsonify({"deleted": True}), 200

    @app.get("/categories")
    def list_categories():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE user_id = %s ORDER BY id", (user_id,))
            categories = cursor.fetchall()

        return jsonify(categories), 200

    @app.post("/categories")
    def create_category():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        name = str(payload.get("name", "")).strip()
        color = str(payload.get("color", "#3498db")).strip()

        if not name:
            return jsonify({"error": "category name is required"}), 400

        if not (color.startswith("#") and len(color) == 7):
            color = "#3498db"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO categories (name, color, user_id) VALUES (%s, %s, %s)",
                (name, color, user_id)
            )
            category_id = cursor.lastrowid

            cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
            category = cursor.fetchone()

        return jsonify(category), 201

    @app.get("/categories/<int:category_id>")
    def get_category(category_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE id = %s AND user_id = %s", (category_id, user_id))
            category = cursor.fetchone()

        if not category:
            return jsonify({"error": "category not found"}), 404

        return jsonify(category), 200

    @app.patch("/categories/<int:category_id>")
    def update_category(category_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE id = %s AND user_id = %s", (category_id, user_id))
            category = cursor.fetchone()

            if not category:
                return jsonify({"error": "category not found"}), 404

            updates = []
            values = []

            if "name" in payload:
                name = str(payload["name"]).strip()
                if not name:
                    return jsonify({"error": "category name cannot be empty"}), 400
                updates.append("name = %s")
                values.append(name)

            if "color" in payload:
                color = str(payload["color"]).strip()
                if color.startswith("#") and len(color) == 7:
                    updates.append("color = %s")
                    values.append(color)

            if not updates:
                return jsonify(category), 200

            values.append(category_id)
            query = f"UPDATE categories SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, values)

            cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
            updated_category = cursor.fetchone()

        return jsonify(updated_category), 200

    @app.delete("/categories/<int:category_id>")
    def delete_category(category_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE id = %s AND user_id = %s", (category_id, user_id))
            if not cursor.fetchone():
                return jsonify({"error": "category not found"}), 404

            cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))

        return jsonify({"deleted": True}), 200

    @app.get("/user/settings")
    def get_user_settings():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, display_name, dark_mode FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

        if not user:
            return jsonify({"error": "user not found"}), 404

        return jsonify({"display_name": user["display_name"], "dark_mode": user["dark_mode"]}), 200

    @app.patch("/user/settings")
    def update_user_settings():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        with get_db() as conn:
            cursor = conn.cursor()
            updates = []
            values = []

            if "display_name" in payload:
                display_name = str(payload["display_name"]).strip()
                if not display_name:
                    return jsonify({"error": "display name cannot be empty"}), 400
                updates.append("display_name = %s")
                values.append(display_name)

            if "dark_mode" in payload:
                updates.append("dark_mode = %s")
                values.append(payload["dark_mode"])

            if not updates:
                cursor.execute("SELECT id, display_name, dark_mode FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                return jsonify({"display_name": user["display_name"], "dark_mode": user["dark_mode"]}), 200

            values.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(query, values)

            cursor.execute("SELECT id, display_name, dark_mode FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

        return jsonify({"display_name": user["display_name"], "dark_mode": user["dark_mode"]}), 200

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
