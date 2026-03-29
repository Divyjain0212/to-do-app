import csv
import io
import json
import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from pythonjsonlogger import jsonlogger
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, create_engine, inspect, select, text, update
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from authlib.integrations.flask_client import OAuth
except ImportError:
    OAuth = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#3498db", nullable=False)  # HEX color
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="medium", nullable=False)  # low, medium, high
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    todo_id: Mapped[int] = mapped_column(ForeignKey("todos.id", ondelete="CASCADE"), nullable=False, index=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TaskShare(Base):
    __tablename__ = "task_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    todo_id: Mapped[int] = mapped_column(ForeignKey("todos.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shared_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    google_sub: Mapped[str] = mapped_column(String(255), nullable=True, unique=True)
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


def _build_database_url() -> str:
    """Build database URL with preference for MySQL/RDS in production."""
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    # RDS/MySQL configuration (production)
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_port = os.getenv("DB_PORT", "3306")

    if db_host and db_name and db_user and db_password:
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # Local SQLite for development
    sqlite_path = Path(__file__).resolve().parents[1] / "todo.db"
    return f"sqlite+pysqlite:///{sqlite_path.as_posix()}"


def _create_db_engine(database_url: str):
    if database_url.startswith("sqlite"):
        return create_engine(database_url, connect_args={"check_same_thread": False})

    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )


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


def _load_environment() -> None:
    env_file = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_file, override=False)


def _ensure_schema_compatibility(engine) -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    with engine.begin() as connection:
        if "todos" in table_names:
            todo_columns = {column["name"] for column in inspector.get_columns("todos")}
            if "user_id" not in todo_columns:
                connection.execute(text("ALTER TABLE todos ADD COLUMN user_id INTEGER NULL"))
            if "description" not in todo_columns:
                connection.execute(text("ALTER TABLE todos ADD COLUMN description VARCHAR(1000) NULL"))
            if "priority" not in todo_columns:
                connection.execute(text("ALTER TABLE todos ADD COLUMN priority VARCHAR(10) NOT NULL DEFAULT 'medium'"))
            if "due_date" not in todo_columns:
                connection.execute(text("ALTER TABLE todos ADD COLUMN due_date DATETIME NULL"))
            if "created_at" not in todo_columns:
                connection.execute(text("ALTER TABLE todos ADD COLUMN created_at DATETIME NULL"))
                connection.execute(text("UPDATE todos SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
            if "updated_at" not in todo_columns:
                connection.execute(text("ALTER TABLE todos ADD COLUMN updated_at DATETIME NULL"))
                connection.execute(text("UPDATE todos SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
            if "category_id" not in todo_columns:
                connection.execute(text("ALTER TABLE todos ADD COLUMN category_id INTEGER NULL"))

        if "users" in table_names:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "dark_mode" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN dark_mode BOOLEAN NOT NULL DEFAULT 0"))
            if "created_at" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME NULL"))
                connection.execute(text("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))


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
    app.logger = _configure_logger()
    app.config["SQLALCHEMY_DATABASE_URL"] = _build_database_url()
    app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET", "")
    app.config["GOOGLE_REDIRECT_URI"] = os.getenv("GOOGLE_REDIRECT_URI", "")

    app.engine = _create_db_engine(app.config["SQLALCHEMY_DATABASE_URL"])
    try:
        Base.metadata.create_all(app.engine)
    except OperationalError as exc:
        # SQLite can hit a startup race when multiple gunicorn workers call create_all.
        # If the table was created by another worker just before this statement, continue.
        if "already exists" not in str(exc).lower():
            raise
    _ensure_schema_compatibility(app.engine)

    oauth = OAuth(app) if OAuth is not None else None
    google_enabled = bool(
        oauth is not None and app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"]
    )
    if oauth is None:
        app.logger.warning(
            "Authlib is not installed; Google OAuth endpoints are disabled",
            extra={"request_id": "startup"},
        )
    elif google_enabled:
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    app.logger.info(
        "Application started",
        extra={"request_id": "startup", "db_backend": app.engine.dialect.name},
    )

    @app.before_request
    def add_request_id() -> None:
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.user_id = session.get("user_id")
        session.permanent = True

    @app.after_request
    def set_request_headers(response):
        response.headers["X-Request-ID"] = g.request_id
        return response

    @contextmanager
    def session_scope():
        session = Session(app.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _current_user_id() -> Optional[int]:
        user_id = session.get("user_id")
        if isinstance(user_id, int):
            return user_id
        return None

    def _require_auth() -> Optional[tuple]:
        if _current_user_id() is None:
            return jsonify({"error": "authentication required"}), 401
        return None

    @app.get("/health")
    def health():
        try:
            with session_scope() as session:
                session.execute(select(1))
            return jsonify({"status": "ok"}), 200
        except SQLAlchemyError as exc:
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
        return (
            jsonify(
                {
                    "service": "todo-app",
                    "status": "running",
                    "endpoints": [
                        "/",
                        "/app",
                        "/api",
                        "/health",
                        "/auth/me",
                        "/auth/signup",
                        "/auth/login",
                        "/auth/logout",
                        "/auth/google/login",
                        "/todos",
                    ],
                    "google_auth_enabled": google_enabled,
                }
            ),
            200,
        )

    @app.get("/auth/me")
    def auth_me():
        user_id = _current_user_id()
        if user_id is None:
            return jsonify({"authenticated": False, "google_auth_enabled": google_enabled}), 200

        with session_scope() as db_session:
            user = db_session.get(User, user_id)
            if user is None:
                session.clear()
                return jsonify({"authenticated": False, "google_auth_enabled": google_enabled}), 200

            return (
                jsonify(
                    {
                        "authenticated": True,
                        "google_auth_enabled": google_enabled,
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "display_name": user.display_name,
                            "dark_mode": user.dark_mode,
                        },
                    }
                ),
                200,
            )

    @app.post("/auth/signup")
    def auth_signup():
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", "")).strip()
        display_name = str(payload.get("display_name", "")).strip() or email.split("@")[0]

        if not email or "@" not in email:
            return jsonify({"error": "valid email is required"}), 400
        if len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters"}), 400

        with session_scope() as db_session:
            existing = db_session.scalar(select(User).where(User.email == email))
            if existing is not None:
                return jsonify({"error": "email already registered"}), 409

            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                display_name=display_name,
                dark_mode=False,
            )
            db_session.add(user)
            db_session.flush()
            session["user_id"] = user.id

            return (
                jsonify(
                    {
                        "authenticated": True,
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "display_name": user.display_name,
                            "dark_mode": user.dark_mode,
                        },
                    }
                ),
                201,
            )

    @app.post("/auth/login")
    def auth_login():
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", "")).strip()

        with session_scope() as db_session:
            user = db_session.scalar(select(User).where(User.email == email))
            if user is None or not user.password_hash or not check_password_hash(user.password_hash, password):
                return jsonify({"error": "invalid credentials"}), 401

            session["user_id"] = user.id
            return (
                jsonify(
                    {
                        "authenticated": True,
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "display_name": user.display_name,
                            "dark_mode": user.dark_mode,
                        },
                    }
                ),
                200,
            )

    @app.post("/auth/logout")
    def auth_logout():
        session.clear()
        return jsonify({"authenticated": False}), 200

    @app.get("/auth/google/login")
    def auth_google_login():
        if not google_enabled:
            return jsonify({"error": "google auth is not configured"}), 400

        dynamic_redirect_uri = url_for("auth_google_callback", _external=True)
        configured_redirect_uri = (app.config["GOOGLE_REDIRECT_URI"] or "").strip()
        loopback_hosts = {"127.0.0.1", "localhost", "::1"}

        # Enforce one canonical OAuth host from GOOGLE_REDIRECT_URI so the callback
        # always lands on the same host where session state was created.
        redirect_uri = dynamic_redirect_uri
        if configured_redirect_uri:
            try:
                configured = urlparse(configured_redirect_uri)
                current = urlparse(dynamic_redirect_uri)
                configured_callback_path = url_for("auth_google_callback")

                if configured.path != configured_callback_path:
                    app.logger.error(
                        "Configured Google redirect URI path is invalid",
                        extra={
                            "request_id": g.request_id,
                            "configured_redirect_uri": configured_redirect_uri,
                            "expected_path": configured_callback_path,
                        },
                    )
                    return jsonify({"error": "google auth redirect uri is misconfigured"}), 500

                # For local development, prefer current loopback host+port to avoid
                # forcing stale values (for example 8081 after moving to 8000).
                if (
                    configured.hostname in loopback_hosts
                    and current.hostname in loopback_hosts
                    and configured.scheme == current.scheme
                ):
                    redirect_uri = dynamic_redirect_uri
                elif configured.scheme != current.scheme or configured.netloc != current.netloc:
                    canonical_login_url = f"{configured.scheme}://{configured.netloc}{url_for('auth_google_login')}"
                    app.logger.info(
                        "Redirecting to canonical OAuth host",
                        extra={
                            "request_id": g.request_id,
                            "from_host": current.netloc,
                            "to_host": configured.netloc,
                        },
                    )
                    return redirect(canonical_login_url)
                else:
                    redirect_uri = configured_redirect_uri
            except Exception as exc:
                app.logger.warning(
                    "Invalid configured Google redirect URI; using dynamic callback URL",
                    extra={
                        "request_id": g.request_id,
                        "error": str(exc),
                        "configured_redirect_uri": configured_redirect_uri,
                        "dynamic_redirect_uri": dynamic_redirect_uri,
                    },
                )

        return oauth.google.authorize_redirect(redirect_uri)

    @app.get("/auth/google/callback")
    def auth_google_callback():
        if not google_enabled:
            return jsonify({"error": "google auth is not configured"}), 400

        try:
            token = oauth.google.authorize_access_token()
        except Exception as exc:
            app.logger.error(
                "Google OAuth callback failed",
                extra={"request_id": g.request_id, "error": str(exc)},
            )
            if "mismatching_state" in str(exc):
                return (
                    jsonify(
                        {
                            "error": "google authentication failed",
                            "details": "oauth state mismatch; retry login from a single host (127.0.0.1 or localhost) and clear old cookies",
                        }
                    ),
                    401,
                )
            return jsonify({"error": "google authentication failed"}), 401

        user_info = token.get("userinfo")
        if not user_info:
            user_info = oauth.google.userinfo()

        email = str(user_info.get("email", "")).strip().lower()
        google_sub = str(user_info.get("sub", "")).strip()
        name = str(user_info.get("name", "")).strip() or email.split("@")[0]

        email_verified = bool(user_info.get("email_verified", False))

        if not email or not google_sub or not email_verified:
            return jsonify({"error": "unable to read google user profile"}), 400

        with session_scope() as db_session:
            user = db_session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    display_name=name,
                    google_sub=google_sub,
                    password_hash=None,
                    dark_mode=False,
                )
                db_session.add(user)
                db_session.flush()
            else:
                user.google_sub = google_sub
                if not user.display_name:
                    user.display_name = name

            session["user_id"] = user.id

        return redirect(url_for("index"))

    @app.get("/todos")
    def list_todos():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        
        # Query parameters for filtering
        search = request.args.get("search", "").strip()
        category_id = request.args.get("category_id", type=int)
        priority = request.args.get("priority", "").strip()
        completed = request.args.get("completed", type=lambda x: x.lower() == "true")
        sort_by = request.args.get("sort_by", "created_at")  # created_at, due_date, priority
        export_format = request.args.get("export", "").strip()
        
        with session_scope() as db_session:
            query = select(Todo).where(Todo.user_id == user_id)
            
            # Apply filters
            if search:
                query = query.where(Todo.title.ilike(f"%{search}%"))
            if category_id:
                query = query.where(Todo.category_id == category_id)
            if priority:
                query = query.where(Todo.priority == priority)
            if completed is not None:
                query = query.where(Todo.completed == completed)
            
            # Apply sorting
            if sort_by == "due_date":
                query = query.order_by(Todo.due_date.asc())
            elif sort_by == "priority":
                query = query.order_by(Todo.priority.asc())
            else:  # created_at (default)
                query = query.order_by(Todo.created_at.desc())
            
            todos = db_session.scalars(query).all()
            
            # Handle export
            if export_format == "json":
                data = [{
                    "id": todo.id,
                    "title": todo.title,
                    "description": todo.description,
                    "completed": todo.completed,
                    "priority": todo.priority,
                    "due_date": todo.due_date.isoformat() if todo.due_date else None,
                    "created_at": todo.created_at.isoformat(),
                    "category_id": todo.category_id,
                } for todo in todos]
                
                response = jsonify(data)
                response.headers["Content-Disposition"] = f"attachment;filename=todos-{datetime.utcnow().strftime('%Y%m%d')}.json"
                return response, 200
            
            elif export_format == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["ID", "Title", "Description", "Completed", "Priority", "Due Date", "Created At"])
                
                for todo in todos:
                    writer.writerow([
                        todo.id,
                        todo.title,
                        todo.description or "",
                        "Yes" if todo.completed else "No",
                        todo.priority,
                        todo.due_date.strftime("%Y-%m-%d") if todo.due_date else "",
                        todo.created_at.strftime("%Y-%m-%d %H:%M"),
                    ])
                
                response = jsonify({"csv": output.getvalue()})
                response.headers["Content-Disposition"] = f"attachment;filename=todos-{datetime.utcnow().strftime('%Y%m%d')}.csv"
                return response, 200
            
            # Normal JSON response
            result = [{
                "id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "completed": todo.completed,
                "priority": todo.priority,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "created_at": todo.created_at.isoformat(),
                "category_id": todo.category_id,
            } for todo in todos]
            return jsonify(result), 200

    @app.post("/todos")
    def create_todo():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}
        title = payload.get("title", "").strip()
        
        if not title:
            return jsonify({"error": "title is required"}), 400

        description = payload.get("description", "").strip() or None
        priority = payload.get("priority", "medium").strip() or "medium"
        raw_category_id = payload.get("category_id")
        try:
            if raw_category_id in (None, ""):
                category_id = None
            else:
                category_id = int(raw_category_id)
        except (TypeError, ValueError):
            return jsonify({"error": "invalid category_id"}), 400
        due_date_str = payload.get("due_date")
        
        # Validate priority
        if priority not in ["low", "medium", "high"]:
            priority = "medium"
        
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str)
            except (ValueError, TypeError):
                return jsonify({"error": "invalid due_date format"}), 400

        with session_scope() as db_session:
            # Verify category ownership if provided
            if category_id:
                category = db_session.get(Category, category_id)
                if not category or category.user_id != user_id:
                    return jsonify({"error": "category not found"}), 404
            
            todo = Todo(
                title=title,
                description=description,
                completed=bool(payload.get("completed", False)),
                priority=priority,
                due_date=due_date,
                user_id=user_id,
                category_id=category_id,
            )
            db_session.add(todo)
            db_session.flush()
            
            return jsonify({
                "id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "completed": todo.completed,
                "priority": todo.priority,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "created_at": todo.created_at.isoformat(),
                "category_id": todo.category_id,
            }), 201

    @app.patch("/todos/<int:todo_id>")
    def update_todo(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        with session_scope() as db_session:
            todo = db_session.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id))
            if todo is None:
                return jsonify({"error": "todo not found"}), 404

            if "title" in payload:
                title = str(payload["title"]).strip()
                if not title:
                    return jsonify({"error": "title cannot be empty"}), 400
                todo.title = title

            if "description" in payload:
                todo.description = str(payload["description"]).strip() or None

            if "completed" in payload:
                todo.completed = bool(payload["completed"])

            if "priority" in payload:
                priority = str(payload["priority"]).strip().lower()
                if priority in ["low", "medium", "high"]:
                    todo.priority = priority

            if "due_date" in payload:
                due_date_str = payload["due_date"]
                if due_date_str:
                    try:
                        todo.due_date = datetime.fromisoformat(due_date_str)
                    except (ValueError, TypeError):
                        return jsonify({"error": "invalid due_date format"}), 400
                else:
                    todo.due_date = None

            if "category_id" in payload:
                category_id = payload["category_id"]
                if category_id:
                    category = db_session.get(Category, category_id)
                    if not category or category.user_id != user_id:
                        return jsonify({"error": "category not found"}), 404
                    todo.category_id = category_id
                else:
                    todo.category_id = None

            todo.updated_at = datetime.utcnow()
            db_session.add(todo)
            
            return jsonify({
                "id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "completed": todo.completed,
                "priority": todo.priority,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "created_at": todo.created_at.isoformat(),
                "updated_at": todo.updated_at.isoformat(),
                "category_id": todo.category_id,
            }), 200

    @app.delete("/todos/<int:todo_id>")
    def delete_todo(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        with session_scope() as db_session:
            todo = db_session.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id))
            if todo is None:
                return jsonify({"error": "todo not found"}), 404
            db_session.delete(todo)
            return "", 204

    @app.get("/categories")
    def list_categories():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        with session_scope() as db_session:
            categories = db_session.scalars(select(Category).where(Category.user_id == user_id)).all()
            result = [{"id": cat.id, "name": cat.name, "color": cat.color} for cat in categories]
            return jsonify(result), 200

    @app.post("/categories")
    def create_category():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}
        name = payload.get("name", "").strip()
        color = payload.get("color", "#3498db").strip()

        if not name:
            return jsonify({"error": "category name is required"}), 400

        if not color.startswith("#") or len(color) != 7:
            color = "#3498db"

        with session_scope() as db_session:
            category = Category(name=name, color=color, user_id=user_id)
            db_session.add(category)
            db_session.flush()
            return jsonify({"id": category.id, "name": category.name, "color": category.color}), 201

    @app.patch("/categories/<int:category_id>")
    def update_category(category_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        with session_scope() as db_session:
            category = db_session.get(Category, category_id)
            if not category or category.user_id != user_id:
                return jsonify({"error": "category not found"}), 404

            if "name" in payload:
                name = str(payload["name"]).strip()
                if not name:
                    return jsonify({"error": "category name cannot be empty"}), 400
                category.name = name

            if "color" in payload:
                color = str(payload["color"]).strip()
                if color.startswith("#") and len(color) == 7:
                    category.color = color

            db_session.add(category)
            return jsonify({"id": category.id, "name": category.name, "color": category.color}), 200

    @app.delete("/categories/<int:category_id>")
    def delete_category(category_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        with session_scope() as db_session:
            category = db_session.get(Category, category_id)
            if not category or category.user_id != user_id:
                return jsonify({"error": "category not found"}), 404
            
            # Remove category from todos
            db_session.execute(
                update(Todo)
                .where(Todo.category_id == category_id, Todo.user_id == user_id)
                .values(category_id=None)
            )
            db_session.delete(category)
            return "", 204

    @app.post("/todos/<int:todo_id>/reminders")
    def create_reminder(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}
        remind_at_str = payload.get("remind_at")

        if not remind_at_str:
            return jsonify({"error": "remind_at is required"}), 400

        with session_scope() as db_session:
            todo = db_session.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id))
            if not todo:
                return jsonify({"error": "todo not found"}), 404

            try:
                remind_at = datetime.fromisoformat(remind_at_str)
            except (ValueError, TypeError):
                return jsonify({"error": "invalid remind_at format"}), 400

            reminder = Reminder(todo_id=todo_id, remind_at=remind_at)
            db_session.add(reminder)
            db_session.flush()
            return jsonify({"id": reminder.id, "remind_at": reminder.remind_at.isoformat()}), 201

    @app.get("/todos/<int:todo_id>/reminders")
    def list_reminders(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        with session_scope() as db_session:
            todo = db_session.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id))
            if not todo:
                return jsonify({"error": "todo not found"}), 404

            reminders = db_session.scalars(select(Reminder).where(Reminder.todo_id == todo_id)).all()
            result = [{"id": r.id, "remind_at": r.remind_at.isoformat(), "sent": r.sent} for r in reminders]
            return jsonify(result), 200

    @app.delete("/reminders/<int:reminder_id>")
    def delete_reminder(reminder_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        with session_scope() as db_session:
            reminder = db_session.get(Reminder, reminder_id)
            if not reminder:
                return jsonify({"error": "reminder not found"}), 404
            
            todo = db_session.get(Todo, reminder.todo_id)
            if not todo or todo.user_id != user_id:
                return jsonify({"error": "unauthorized"}), 403
            
            db_session.delete(reminder)
            return "", 204

    @app.post("/todos/<int:todo_id>/share")
    def share_todo(todo_id: int):
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}
        shared_with_email = payload.get("email", "").strip().lower()
        can_edit = bool(payload.get("can_edit", False))

        if not shared_with_email:
            return jsonify({"error": "email is required"}), 400

        with session_scope() as db_session:
            todo = db_session.scalar(select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id))
            if not todo:
                return jsonify({"error": "todo not found"}), 404

            shared_user = db_session.scalar(select(User).where(User.email == shared_with_email))
            if not shared_user:
                return jsonify({"error": "user not found"}), 404

            if shared_user.id == user_id:
                return jsonify({"error": "cannot share with yourself"}), 400

            # Check if already shared
            existing = db_session.scalar(
                select(TaskShare).where(
                    TaskShare.todo_id == todo_id,
                    TaskShare.shared_with_user_id == shared_user.id
                )
            )
            if existing:
                existing.can_edit = can_edit
                db_session.add(existing)
            else:
                share = TaskShare(todo_id=todo_id, shared_with_user_id=shared_user.id, can_edit=can_edit)
                db_session.add(share)

            db_session.flush()
            return jsonify({"message": "todo shared successfully"}), 201

    @app.get("/todos/shared")
    def list_shared_todos():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        with session_scope() as db_session:
            shares = db_session.scalars(select(TaskShare).where(TaskShare.shared_with_user_id == user_id)).all()
            result = []
            for share in shares:
                todo = db_session.get(Todo, share.todo_id)
                if todo:
                    result.append({
                        "id": todo.id,
                        "title": todo.title,
                        "description": todo.description,
                        "completed": todo.completed,
                        "priority": todo.priority,
                        "due_date": todo.due_date.isoformat() if todo.due_date else None,
                        "can_edit": share.can_edit,
                        "shared_by_id": todo.user_id,
                    })
            return jsonify(result), 200

    @app.get("/user/settings")
    def get_user_settings():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        with session_scope() as db_session:
            user = db_session.get(User, user_id)
            if not user:
                return jsonify({"error": "user not found"}), 404

            return jsonify({
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "dark_mode": user.dark_mode,
            }), 200

    @app.patch("/user/settings")
    def update_user_settings():
        unauthenticated = _require_auth()
        if unauthenticated is not None:
            return unauthenticated

        user_id = _current_user_id()
        payload = request.get_json(silent=True) or {}

        with session_scope() as db_session:
            user = db_session.get(User, user_id)
            if not user:
                return jsonify({"error": "user not found"}), 404

            if "display_name" in payload:
                display_name = str(payload["display_name"]).strip()
                if display_name:
                    user.display_name = display_name

            if "dark_mode" in payload:
                user.dark_mode = bool(payload["dark_mode"])

            db_session.add(user)
            return jsonify({
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "dark_mode": user.dark_mode,
            }), 200

    @app.errorhandler(404)
    def not_found(_error):
        return (
            jsonify(
                {
                    "error": "not found",
                    "message": "Use one of the known endpoints.",
                    "endpoints": ["/", "/app", "/api", "/health", "/auth/me", "/todos"],
                }
            ),
            404,
        )

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
