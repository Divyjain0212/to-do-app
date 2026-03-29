const signinForm = document.getElementById("signin-form");
const signupForm = document.getElementById("signup-form");
const googleLoginBtn = document.getElementById("google-login");
const statusText = document.getElementById("status");

let googleAuthEnabled = false;

function setStatus(message, isError = false) {
  if (!statusText) return;
  statusText.textContent = message;
  statusText.classList.toggle("is-error", isError);
  statusText.classList.toggle("is-success", !isError && Boolean(message));
}

async function fetchMe() {
  const response = await fetch("/auth/me");
  if (!response.ok) {
    throw new Error("Unable to read session state.");
  }
  return response.json();
}

async function bootstrapLanding() {
  try {
    const state = await fetchMe();
    googleAuthEnabled = Boolean(state.google_auth_enabled);
    if (googleLoginBtn) {
      googleLoginBtn.disabled = !googleAuthEnabled;
      googleLoginBtn.title = googleAuthEnabled ? "Sign in with Google" : "Google login not configured";
    }

    if (state.authenticated) {
      window.location.replace("/app");
    }
  } catch (error) {
    setStatus(error.message, true);
  }
}

if (signinForm) {
  signinForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("signin-email")?.value?.trim() || "";
    const password = document.getElementById("signin-password")?.value || "";

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Sign in failed.");
      }

      setStatus("Signed in. Redirecting...");
      window.location.href = "/app";
    } catch (error) {
      setStatus(error.message, true);
    }
  });
}

if (signupForm) {
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const displayName = document.getElementById("signup-name")?.value?.trim() || "";
    const email = document.getElementById("signup-email")?.value?.trim() || "";
    const password = document.getElementById("signup-password")?.value || "";

    try {
      const response = await fetch("/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: displayName, email, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Sign up failed.");
      }

      setStatus("Account created. Redirecting...");
      window.location.href = "/app";
    } catch (error) {
      setStatus(error.message, true);
    }
  });
}

if (googleLoginBtn) {
  googleLoginBtn.addEventListener("click", () => {
    if (!googleAuthEnabled) {
      setStatus("Google login is not configured.", true);
      return;
    }
    window.location.href = "/auth/google/login";
  });
}

document.addEventListener("DOMContentLoaded", bootstrapLanding);
