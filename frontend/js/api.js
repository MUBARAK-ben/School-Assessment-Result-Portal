// Change to your live Render URL once deployed
const API_BASE =
  window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : "https://school-assessment-result-portal.onrender.com";

function getToken() {
  return localStorage.getItem("portal_token");
}

function setSession(token, user) {
  localStorage.setItem("portal_token", token);
  localStorage.setItem("portal_user", JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem("portal_token");
  localStorage.removeItem("portal_user");
}

function getSavedUser() {
  const raw = localStorage.getItem("portal_user");
  return raw ? JSON.parse(raw) : null;
}

async function apiRequest(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}