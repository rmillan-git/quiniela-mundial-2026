const auth = {
  async getUser() {
    const cached = localStorage.getItem("user");
    if (cached) return JSON.parse(cached);
    if (!localStorage.getItem("token")) return null;
    const user = await api.get("/auth/me");
    if (user.id) {
      localStorage.setItem("user", JSON.stringify(user));
      return user;
    }
    localStorage.removeItem("token");
    return null;
  },

  async init() {
    const user = await this.getUser();
    const logoutBtn = document.getElementById("btn-logout");
    const loginBtn = document.getElementById("nav-login");
    const adminBtn = document.getElementById("nav-admin");

    if (logoutBtn) logoutBtn.addEventListener("click", () => api.logout());

    if (user) {
      if (loginBtn) loginBtn.classList.add("d-none");
      if (logoutBtn) logoutBtn.classList.remove("d-none");
      if (adminBtn && user.is_admin) adminBtn.classList.remove("d-none");
    }
  },
};

document.addEventListener("DOMContentLoaded", () => auth.init());
