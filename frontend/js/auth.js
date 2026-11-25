function showBanner(msg, isError = false) {
  const banner = document.getElementById("banner");
  banner.textContent = msg;
  banner.className = `banner ${isError ? "err" : "ok"}`;
}

function hideBanner() {
  document.getElementById("banner").className = "banner hidden";
}

async function checkApiStatus() {
  const badge = document.getElementById("apiBadge");
  try {
    await apiRequest("/health");
    badge.textContent = "API Online";
  } catch {
    badge.textContent = "API Offline";
  }
}

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideBanner();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value;

  try {
    const res = await apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setSession(res.access_token, res.user);
    await routeByRole(res.user);
  } catch (err) {
    showBanner(err.message, true);
  }
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  clearSession();
  location.reload();
});