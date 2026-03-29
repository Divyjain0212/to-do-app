// DOM Elements
const todoList = document.getElementById("todo-list");
const todoForm = document.getElementById("todo-form");
const todoTitle = document.getElementById("todo-title");
const todoPriority = document.getElementById("todo-priority");
const todoCategory = document.getElementById("todo-category");
const todoDueDate = document.getElementById("todo-due-date");
const statusText = document.getElementById("status");
const authPanel = document.getElementById("auth-panel");
const todoPanel = document.getElementById("todo-panel");
const signinForm = document.getElementById("signin-form");
const signupForm = document.getElementById("signup-form");
const logoutBtn = document.getElementById("logout-btn");
const googleLoginBtn = document.getElementById("google-login");
const userName = document.getElementById("user-name");
const userEmail = document.getElementById("user-email");
const statTotal = document.getElementById("stat-total");
const statActive = document.getElementById("stat-active");
const statCompleted = document.getElementById("stat-completed");
const filterButtons = document.querySelectorAll(".filter-btn");
const priorityFilter = document.getElementById("priority-filter");
const categoryFilter = document.getElementById("category-filter");
const searchInput = document.getElementById("search-input");
const darkModeToggle = document.getElementById("dark-mode-toggle");
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const settingsForm = document.getElementById("settings-form");
const closeModalBtn = document.getElementById("close-modal");
const categoriesList = document.getElementById("categories-list");
const categoryForm = document.getElementById("category-form");
const categoryName = document.getElementById("category-name");
const categoryColor = document.getElementById("category-color");
const exportJsonBtn = document.getElementById("export-json");
const exportCsvBtn = document.getElementById("export-csv");

// State
let currentUser = null;
let googleAuthEnabled = false;
let currentFilter = "all";
let currentPriorityFilter = "";
let currentCategoryFilter = "";
let currentSearch = "";
let lastTodos = [];
let allCategories = [];

function setStatus(message, isError = false) {
  if (!statusText) return;
  statusText.textContent = message;
  statusText.classList.toggle("is-error", isError);
  statusText.classList.toggle("is-success", !isError && Boolean(message));
}

async function fetchTodos(params = {}) {
  const url = new URL("/todos", window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value) url.searchParams.append(key, value);
  });

  const response = await fetch(url.toString());
  if (response.status === 401) {
    currentUser = null;
    applyAuthState();
    throw new Error("Please sign in to view your todos.");
  }
  if (!response.ok) throw new Error("Unable to load todos.");
  return response.json();
}

async function fetchCategories() {
  const response = await fetch("/categories");
  if (!response.ok) throw new Error("Unable to load categories.");
  return response.json();
}

async function fetchMe() {
  const response = await fetch("/auth/me");
  if (!response.ok) throw new Error("Unable to read session state.");
  return response.json();
}

async function createTodo(todoData) {
  const response = await fetch("/todos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(todoData),
  });
  if (!response.ok) throw new Error("Unable to create todo.");
  return response.json();
}

async function updateTodo(id, changes) {
  const response = await fetch(`/todos/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  if (!response.ok) throw new Error("Unable to update todo.");
  return response.json();
}

async function deleteTodo(id) {
  const response = await fetch(`/todos/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Unable to delete todo.");
}

async function createCategory(name, color) {
  const response = await fetch("/categories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, color }),
  });
  if (!response.ok) throw new Error("Unable to create category.");
  return response.json();
}

async function deleteCategory(id) {
  const response = await fetch(`/categories/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Unable to delete category.");
}

async function getUserSettings() {
  const response = await fetch("/user/settings");
  if (!response.ok) throw new Error("Unable to load settings.");
  return response.json();
}

async function updateUserSettings(changes) {
  const response = await fetch("/user/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  if (!response.ok) throw new Error("Unable to update settings.");
  return response.json();
}

async function bootstrapAuth() {
  try {
    const authState = await fetchMe();
    if (authState.authenticated) {
      currentUser = authState.user;
      googleAuthEnabled = authState.google_auth_enabled;
      await loadUserData();
    } else {
      googleAuthEnabled = authState.google_auth_enabled;
    }
  } catch (e) {
    setStatus(`Auth check failed: ${e.message}`, true);
  }
  applyAuthState();
}

async function loadUserData() {
  try {
    lastTodos = await fetchTodos();
    allCategories = await fetchCategories();
    await refreshUI();
  } catch (e) {
    setStatus(`Failed to load data: ${e.message}`, true);
  }
}

function updateStats() {
  const total = lastTodos.length;
  const completed = lastTodos.filter((t) => t.completed).length;
  const active = total - completed;

  if (statTotal) statTotal.textContent = total;
  if (statActive) statActive.textContent = active;
  if (statCompleted) statCompleted.textContent = completed;
}

function applyAuthState() {
  if (currentUser) {
    if (authPanel) authPanel.classList.add("hidden");
    if (todoPanel) todoPanel.classList.remove("hidden");
    if (userName) userName.textContent = currentUser.display_name || currentUser.email;
    if (userEmail) userEmail.textContent = currentUser.email;
    // Apply dark mode preference
    if (currentUser.dark_mode) {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }
  } else {
    if (authPanel) authPanel.classList.remove("hidden");
    if (todoPanel) todoPanel.classList.add("hidden");
  }

  if (googleLoginBtn) {
    googleLoginBtn.disabled = !googleAuthEnabled;
    googleLoginBtn.textContent = googleAuthEnabled
      ? "Continue with Google"
      : "Google login not configured";
  }
}

function renderTodos() {
  if (!todoList) return;

  let filtered = lastTodos;

  // Apply search filter
  if (currentSearch) {
    filtered = filtered.filter((t) => t.title.toLowerCase().includes(currentSearch.toLowerCase()));
  }

  // Apply status filter
  if (currentFilter === "active") {
    filtered = filtered.filter((t) => !t.completed);
  } else if (currentFilter === "completed") {
    filtered = filtered.filter((t) => t.completed);
  }

  // Apply priority filter
  if (currentPriorityFilter) {
    filtered = filtered.filter((t) => t.priority === currentPriorityFilter);
  }

  // Apply category filter
  if (currentCategoryFilter) {
    filtered = filtered.filter((t) => String(t.category_id) === currentCategoryFilter);
  }

  todoList.innerHTML = "";

  filtered.forEach((todo) => {
    const li = document.createElement("li");
    li.className = `todo-item priority-${todo.priority}`;
    if (todo.completed) li.classList.add("completed");

    const dueDate = todo.due_date ? new Date(todo.due_date).toLocaleDateString() : "";
    const category = allCategories.find((c) => c.id === todo.category_id);

    li.innerHTML = `
      <input type="checkbox" ${todo.completed ? "checked" : ""} data-id="${todo.id}" class="todo-check">
      <div class="todo-content">
        <div class="todo-title">${escapeHtml(todo.title)}</div>
        ${todo.description ? `<div class="todo-desc">${escapeHtml(todo.description)}</div>` : ""}
        <div class="todo-meta">
          <span class="priority-badge priority-${todo.priority}">${todo.priority}</span>
          ${category ? `<span class="category-badge" style="background-color: ${category.color};">${escapeHtml(category.name)}</span>` : ""}
          ${dueDate ? `<span class="due-date">📅 ${dueDate}</span>` : ""}
        </div>
      </div>
      <button class="delete-btn" data-id="${todo.id}" type="button">✕</button>
    `;

    const checkbox = li.querySelector(".todo-check");
    if (checkbox) {
      checkbox.addEventListener("change", async () => {
        try {
          await updateTodo(todo.id, { completed: checkbox.checked });
          await loadUserData();
          setStatus("Todo updated");
        } catch (e) {
          setStatus(e.message, true);
        }
      });
    }

    const deleteBtn = li.querySelector(".delete-btn");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", async () => {
        try {
          await deleteTodo(todo.id);
          await loadUserData();
          setStatus("Todo deleted");
        } catch (e) {
          setStatus(e.message, true);
        }
      });
    }

    todoList.appendChild(li);
  });

  updateStats();
}

function renderCategories() {
  if (!categoriesList) return;
  categoriesList.innerHTML = "";

  allCategories.forEach((cat) => {
    const div = document.createElement("div");
    div.className = "category-item";
    div.innerHTML = `
      <span class="category-dot" style="background-color: ${cat.color};">●</span>
      <span>${escapeHtml(cat.name)}</span>
      <button class="delete-cat-btn" data-id="${cat.id}" type="button">✕</button>
    `;
    div.querySelector(".delete-cat-btn").addEventListener("click", async () => {
      try {
        await deleteCategory(cat.id);
        await loadUserData();
        setStatus("Category deleted");
      } catch (e) {
        setStatus(e.message, true);
      }
    });
    categoriesList.appendChild(div);
  });

  // Update category selectors
  const categorySelect = document.getElementById("todo-category");
  if (categorySelect) {
    categorySelect.innerHTML = '<option value="">No Category</option>';
    allCategories.forEach((cat) => {
      const option = document.createElement("option");
      option.value = cat.id;
      option.textContent = cat.name;
      categorySelect.appendChild(option);
    });
  }

  // Update category filter
  if (categoryFilter) {
    categoryFilter.innerHTML = '<option value="">All Categories</option>';
    allCategories.forEach((cat) => {
      const option = document.createElement("option");
      option.value = cat.id;
      option.textContent = cat.name;
      categoryFilter.appendChild(option);
    });
  }
}

async function refreshUI() {
  renderCategories();
  renderTodos();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Event Listeners
if (todoForm) {
  todoForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = todoTitle?.value.trim();
    const priority = todoPriority?.value || "medium";
    const categoryId = todoCategory?.value || null;
    const dueDate = todoDueDate?.value || null;

    if (!title) {
      setStatus("Please enter a task title", true);
      return;
    }

    try {
      await createTodo({
        title,
        priority,
        category_id: categoryId ? parseInt(categoryId) : null,
        due_date: dueDate,
      });
      if (todoTitle) todoTitle.value = "";
      if (todoPriority) todoPriority.value = "medium";
      if (todoCategory) todoCategory.value = "";
      if (todoDueDate) todoDueDate.value = "";
      await loadUserData();
      setStatus("Task added!");
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (categoryForm) {
  categoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = categoryName?.value.trim();
    const color = categoryColor?.value || "#3498db";

    if (!name) {
      setStatus("Please enter a category name", true);
      return;
    }

    try {
      await createCategory(name, color);
      if (categoryName) categoryName.value = "";
      await loadUserData();
      setStatus("Category added!");
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (signinForm) {
  signinForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("signin-email")?.value;
    const password = document.getElementById("signin-password")?.value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (response.ok) {
        currentUser = data.user;
        await loadUserData();
        applyAuthState();
        setStatus("Signed in successfully!");
      } else {
        setStatus(data.error || "Sign in failed", true);
      }
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (signupForm) {
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const displayName = document.getElementById("signup-name")?.value;
    const email = document.getElementById("signup-email")?.value;
    const password = document.getElementById("signup-password")?.value;

    try {
      const response = await fetch("/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: displayName, email, password }),
      });

      const data = await response.json();
      if (response.ok) {
        currentUser = data.user;
        await loadUserData();
        applyAuthState();
        setStatus("Account created and signed in!");
      } else {
        setStatus(data.error || "Sign up failed", true);
      }
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
      currentUser = null;
      lastTodos = [];
      applyAuthState();
      setStatus("Signed out");
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (googleLoginBtn) {
  googleLoginBtn.addEventListener("click", () => {
    if (googleAuthEnabled) {
      window.location.href = "/auth/google/login";
    }
  });
}

filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    filterButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    renderTodos();
  });
});

if (priorityFilter) {
  priorityFilter.addEventListener("change", (e) => {
    currentPriorityFilter = e.target.value;
    renderTodos();
  });
}

if (categoryFilter) {
  categoryFilter.addEventListener("change", (e) => {
    currentCategoryFilter = e.target.value;
    renderTodos();
  });
}

if (searchInput) {
  searchInput.addEventListener("input", (e) => {
    currentSearch = e.target.value;
    renderTodos();
  });
}

if (darkModeToggle) {
  darkModeToggle.addEventListener("click", async () => {
    if (currentUser) {
      try {
        const newDarkMode = !currentUser.dark_mode;
        const updated = await updateUserSettings({ dark_mode: newDarkMode });
        currentUser.dark_mode = updated.dark_mode;
        applyAuthState();
        setStatus(newDarkMode ? "Dark mode enabled" : "Dark mode disabled");
      } catch (e) {
        setStatus(e.message, true);
      }
    }
  });
}

if (settingsBtn) {
  settingsBtn.addEventListener("click", async () => {
    try {
      const settings = await getUserSettings();
      if (document.getElementById("settings-display-name")) {
        document.getElementById("settings-display-name").value = settings.display_name;
      }
      if (document.getElementById("settings-dark-mode")) {
        document.getElementById("settings-dark-mode").checked = settings.dark_mode;
      }
      if (settingsModal) settingsModal.classList.remove("hidden");
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (closeModalBtn) {
  closeModalBtn.addEventListener("click", () => {
    if (settingsModal) settingsModal.classList.add("hidden");
  });
}

if (settingsForm) {
  settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const displayName = document.getElementById("settings-display-name")?.value;
    const darkMode = document.getElementById("settings-dark-mode")?.checked;

    try {
      await updateUserSettings({ display_name: displayName, dark_mode: darkMode });
      await bootstrapAuth();
      if (settingsModal) settingsModal.classList.add("hidden");
      setStatus("Settings saved!");
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (exportJsonBtn) {
  exportJsonBtn.addEventListener("click", async () => {
    try {
      const response = await fetch("/todos?export=json");
      if (!response.ok) throw new Error("Export failed");
      const text = await response.text();
      const blob = new Blob([text], { type: "application/json" });
      downloadBlob(blob, `todos-${new Date().toISOString().split("T")[0]}.json`);
      setStatus("Exported as JSON");
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

if (exportCsvBtn) {
  exportCsvBtn.addEventListener("click", async () => {
    try {
      const response = await fetch("/todos?export=csv");
      if (!response.ok) throw new Error("Export failed");
      const data = await response.json();
      const csv = data.csv;
      const blob = new Blob([csv], { type: "text/csv" });
      downloadBlob(blob, `todos-${new Date().toISOString().split("T")[0]}.csv`);
      setStatus("Exported as CSV");
    } catch (e) {
      setStatus(e.message, true);
    }
  });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", bootstrapAuth);
