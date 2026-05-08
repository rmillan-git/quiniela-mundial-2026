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
    const loginBtn = document.getElementById("nav-login");
    const adminBtn = document.getElementById("nav-admin");
    const logoutBtn = document.getElementById("btn-logout");

    if (logoutBtn) logoutBtn.addEventListener("click", () => api.logout());

    if (user) {
      if (loginBtn) loginBtn.classList.add("d-none");
      if (logoutBtn) logoutBtn.classList.add("d-none"); // replaced by dropdown
      if (adminBtn && user.is_admin) adminBtn.classList.remove("d-none");
      this._injectUserDropdown(user);
    }
  },

  _injectUserDropdown(user) {
    // Inject modal for changing password (once, into body)
    if (!document.getElementById("modal-change-pwd")) {
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal fade" id="modal-change-pwd" tabindex="-1">
          <div class="modal-dialog modal-sm">
            <div class="modal-content">
              <div class="modal-header">
                <h6 class="modal-title">🔑 Cambiar Contraseña</h6>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <div class="mb-2">
                  <input type="password" class="form-control form-control-sm" id="cpwd-current" placeholder="Contraseña actual">
                </div>
                <div class="mb-2">
                  <input type="password" class="form-control form-control-sm" id="cpwd-new" placeholder="Nueva contraseña (mín. 6 caracteres)">
                </div>
                <div class="mb-0">
                  <input type="password" class="form-control form-control-sm" id="cpwd-confirm" placeholder="Confirmar nueva contraseña">
                </div>
                <div id="cpwd-alert" class="alert mt-2 d-none"></div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-success btn-sm" id="btn-cpwd-save">Guardar</button>
              </div>
            </div>
          </div>
        </div>`);

      document.getElementById("btn-cpwd-save").addEventListener("click", async () => {
        const current = document.getElementById("cpwd-current").value;
        const newPwd  = document.getElementById("cpwd-new").value;
        const confirm = document.getElementById("cpwd-confirm").value;
        const alertEl = document.getElementById("cpwd-alert");
        alertEl.className = "alert d-none";

        if (!current) { alertEl.className = "alert alert-danger"; alertEl.textContent = "Ingresa tu contraseña actual."; return; }
        if (newPwd.length < 6) { alertEl.className = "alert alert-danger"; alertEl.textContent = "Mínimo 6 caracteres."; return; }
        if (newPwd !== confirm) { alertEl.className = "alert alert-danger"; alertEl.textContent = "Las contraseñas no coinciden."; return; }

        const res = await api.patch("/auth/change-password", { current_password: current, new_password: newPwd });
        if (res.ok) {
          alertEl.className = "alert alert-success";
          alertEl.textContent = "✅ Contraseña actualizada.";
          setTimeout(() => bootstrap.Modal.getInstance(document.getElementById("modal-change-pwd")).hide(), 1200);
        } else {
          alertEl.className = "alert alert-danger";
          alertEl.textContent = res.detail || "Error al cambiar contraseña.";
        }
      });
    }

    // Inject user dropdown before lang-btn in navbar
    const langBtn = document.querySelector(".lang-btn");
    if (!langBtn) return;
    const initials = user.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
    const dropdown = document.createElement("div");
    dropdown.className = "dropdown";
    dropdown.innerHTML = `
      <button class="btn btn-outline-light btn-sm dropdown-toggle d-flex align-items-center gap-1"
              type="button" data-bs-toggle="dropdown">
        <span class="badge bg-light text-dark">${initials}</span>
        <span class="d-none d-md-inline">${user.name.split(" ")[0]}</span>
      </button>
      <ul class="dropdown-menu dropdown-menu-end">
        <li><span class="dropdown-item-text small text-muted">${user.email}</span></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="#" id="nav-change-pwd">🔑 Cambiar Contraseña</a></li>
        <li><a class="dropdown-item text-danger" href="#" id="nav-logout-drop">🚪 Cerrar Sesión</a></li>
      </ul>`;
    langBtn.parentElement.insertBefore(dropdown, langBtn);

    document.getElementById("nav-logout-drop").addEventListener("click", e => { e.preventDefault(); api.logout(); });
    document.getElementById("nav-change-pwd").addEventListener("click", e => {
      e.preventDefault();
      document.getElementById("cpwd-current").value = "";
      document.getElementById("cpwd-new").value = "";
      document.getElementById("cpwd-confirm").value = "";
      document.getElementById("cpwd-alert").className = "alert d-none";
      new bootstrap.Modal(document.getElementById("modal-change-pwd")).show();
    });
  },
};

document.addEventListener("DOMContentLoaded", () => auth.init());
