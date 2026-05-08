const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : "https://quiniela-backend-8oak.onrender.com";

const api = {
  _token() { return localStorage.getItem("token"); },

  _headers(extra = {}) {
    const h = { "Content-Type": "application/json", ...extra };
    const t = this._token();
    if (t) h["Authorization"] = `Bearer ${t}`;
    return h;
  },

  async get(path) {
    try {
      const r = await fetch(API_BASE + path, { headers: this._headers() });
      return r.json();
    } catch (e) { return { error: e.message }; }
  },

  async post(path, body) {
    try {
      const r = await fetch(API_BASE + path, { method: "POST", headers: this._headers(), body: JSON.stringify(body) });
      return r.json();
    } catch (e) { return { error: e.message }; }
  },

  async put(path, body) {
    try {
      const r = await fetch(API_BASE + path, { method: "PUT", headers: this._headers(), body: JSON.stringify(body) });
      return { ok: r.ok, ...(await r.json()) };
    } catch (e) { return { error: e.message }; }
  },

  async patch(path, body) {
    try {
      const r = await fetch(API_BASE + path, { method: "PATCH", headers: this._headers(), body: JSON.stringify(body) });
      return r.json();
    } catch (e) { return { error: e.message }; }
  },

  async delete(path) {
    try {
      const r = await fetch(API_BASE + path, { method: "DELETE", headers: this._headers() });
      return r.json();
    } catch (e) { return { error: e.message }; }
  },

  async login(email, password) {
    const body = new URLSearchParams({ username: email, password });
    try {
      const r = await fetch(API_BASE + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await r.json();
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
        return data;
      }
      return { error: data.detail || "Login failed" };
    } catch (e) { return { error: e.message }; }
  },

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "register.html";
  },
};
