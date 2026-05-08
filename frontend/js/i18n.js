const TRANSLATIONS = {
  es: {
    // Nav
    "nav.groups": "Grupos", "nav.bracket": "Bracket",
    "nav.predictions": "Mis Predicciones", "nav.leaderboard": "Posiciones",
    "nav.login": "Login / Registro", "nav.admin": "Admin", "nav.logout": "Salir",
    // Countdown
    "countdown.days": "días para el Mundial",
    "countdown.today": "🎉 ¡Hoy empieza el Mundial!",
    "countdown.live": "🏆 ¡El Mundial está en curso!",
    // Groups
    "groups.title": "Tablas de Grupos",
    "groups.empty": "La fase de grupos aún no ha comenzado.",
    "groups.col_team": "Equipo",
    "groups.col_played": "J", "groups.col_won": "G", "groups.col_drawn": "E",
    "groups.col_lost": "P", "groups.col_gf": "GF", "groups.col_ga": "GC",
    "groups.col_gd": "DG", "groups.col_pts": "Pts",
    // Bracket
    "bracket.title": "Bracket Eliminatorio",
    "bracket.empty": "La fase eliminatoria aún no ha comenzado.",
    "bracket.r32": "Ronda de 32", "bracket.r16": "Octavos de Final",
    "bracket.qf": "Cuartos de Final", "bracket.sf": "Semifinales",
    "bracket.final": "Final", "bracket.tbd": "Por definir",
    "bracket.r32_paths_title": "Clasificación Ronda de 32",
    // Predictions
    "pred.title": "Mis Predicciones",
    "pred.sub": "Se bloquean al inicio de cada partido",
    "pred.locked": "🔒 Bloqueado",
    "pred.save": "💾 Guardar Predicciones",
    "pred.saving": "Guardando…",
    "pred.login_required": "Inicia sesión para enviar predicciones.",
    "pred.invalid": "Ingresa marcadores válidos (0–20) en todos los campos.",
    "pred.saved_ok": "predicción(es) guardada(s).",
    "pred.saved_err": "guardada(s), error en",
    "pred.round.group_stage": "Fase de Grupos",
    "pred.round.round_of_32": "Ronda de 32",
    "pred.round.round_of_16": "Octavos",
    "pred.round.qf": "Cuartos",
    "pred.round.sf": "Semifinales",
    "pred.round.final": "Final",
    // Admin
    "admin.results_tab": "Resultados",
    "admin.participants_tab": "Participantes",
    "admin.sim_tab": "🎲 Simulación",
    "admin.view_preds": "Ver Quiniela",
    "admin.approve": "Aprobar",
    "admin.remove": "Eliminar",
    "admin.recalc_btn": "🔄 Recalcular Puntos",
    // Register
    "reg.login_title": "Iniciar Sesión",
    "reg.register_title": "Crear Cuenta",
    "reg.login_btn": "Entrar", "reg.register_btn": "Registrarse",
    "reg.no_account": "¿No tienes cuenta?", "reg.register_here": "Regístrate aquí",
    "reg.have_account": "¿Ya tienes cuenta?", "reg.login_link": "Inicia sesión",
    "reg.pending": "Cuenta registrada. Ricardo necesita aprobarla para que puedas enviar predicciones.",
    // Banner & Leaderboard
    "banner.subtitle": "11 jun – 19 jul 2026 · 🇺🇸 🇨🇦 🇲🇽 · 48 equipos · 104 partidos",
    "leaderboard.title": "🏆 Tabla de Posiciones",
    "leaderboard.subtitle": "Actualizada automáticamente después de cada resultado.",
    "leaderboard.col_participant": "Participante",
    "leaderboard.col_groups": "Grupos",
    "leaderboard.col_qf": "CF",
    "leaderboard.col_sf": "SF",
    "leaderboard.col_final": "Final",
    "leaderboard.col_total": "Total",
    "leaderboard.empty": "Aún no hay resultados — los puntos se calculan cuando se ingresan los marcadores.",
  },
  en: {
    "nav.groups": "Groups", "nav.bracket": "Bracket",
    "nav.predictions": "My Predictions", "nav.leaderboard": "Standings",
    "nav.login": "Login / Register", "nav.admin": "Admin", "nav.logout": "Logout",
    "countdown.days": "days to the World Cup",
    "countdown.today": "🎉 The World Cup starts today!",
    "countdown.live": "🏆 The World Cup is live!",
    "groups.title": "Group Tables",
    "groups.empty": "Group stage has not started yet.",
    "groups.col_team": "Team",
    "groups.col_played": "P", "groups.col_won": "W", "groups.col_drawn": "D",
    "groups.col_lost": "L", "groups.col_gf": "GF", "groups.col_ga": "GA",
    "groups.col_gd": "GD", "groups.col_pts": "Pts",
    "bracket.title": "Knockout Bracket",
    "bracket.empty": "Knockout stage has not started yet.",
    "bracket.r32": "Round of 32", "bracket.r16": "Round of 16",
    "bracket.qf": "Quarterfinals", "bracket.sf": "Semifinals",
    "bracket.final": "Final", "bracket.tbd": "TBD",
    "bracket.r32_paths_title": "Round of 32 Qualification",
    "pred.title": "My Predictions",
    "pred.sub": "Locked at kickoff of each match",
    "pred.locked": "🔒 Locked",
    "pred.save": "💾 Save Predictions",
    "pred.saving": "Saving…",
    "pred.login_required": "Please log in to submit predictions.",
    "pred.invalid": "Enter valid scores (0–20) for all fields.",
    "pred.saved_ok": "prediction(s) saved.",
    "pred.saved_err": "saved, error on",
    "pred.round.group_stage": "Group Stage",
    "pred.round.round_of_32": "Round of 32",
    "pred.round.round_of_16": "Round of 16",
    "pred.round.qf": "Quarterfinals",
    "pred.round.sf": "Semifinals",
    "pred.round.final": "Final",
    "admin.results_tab": "Results",
    "admin.participants_tab": "Participants",
    "admin.sim_tab": "🎲 Simulation",
    "admin.view_preds": "View Picks",
    "admin.approve": "Approve",
    "admin.remove": "Remove",
    "admin.recalc_btn": "🔄 Recalculate Points",
    "reg.login_title": "Login",
    "reg.register_title": "Create Account",
    "reg.login_btn": "Login", "reg.register_btn": "Register",
    "reg.no_account": "No account?", "reg.register_here": "Register here",
    "reg.have_account": "Already registered?", "reg.login_link": "Login",
    "reg.pending": "Registered! Ricardo needs to approve your account before you can submit predictions.",
    // Banner & Leaderboard
    "banner.subtitle": "Jun 11 – Jul 19, 2026 · 🇺🇸 🇨🇦 🇲🇽 · 48 teams · 104 matches",
    "leaderboard.title": "🏆 Standings",
    "leaderboard.subtitle": "Updated automatically after each result.",
    "leaderboard.col_participant": "Participant",
    "leaderboard.col_groups": "Groups",
    "leaderboard.col_qf": "QF",
    "leaderboard.col_sf": "SF",
    "leaderboard.col_final": "Final",
    "leaderboard.col_total": "Total",
    "leaderboard.empty": "No results yet — points are calculated when scores are entered.",
  }
};

window.LANG = localStorage.getItem("lang") || "es";

function t(key) {
  return (TRANSLATIONS[window.LANG] || TRANSLATIONS.es)[key] || key;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const val = t(el.getAttribute("data-i18n"));
    if (val) el.textContent = val;
  });
}

function toggleLanguage() {
  window.LANG = window.LANG === "es" ? "en" : "es";
  localStorage.setItem("lang", window.LANG);
  document.querySelectorAll(".lang-btn").forEach(b => {
    b.textContent = window.LANG === "es" ? "🇺🇸 EN" : "🇲🇽 ES";
  });
  applyTranslations();
  document.dispatchEvent(new Event("langchange"));
}

// ── Countdown ────────────────────────────────────────────────────────────────
function getCountdownText() {
  const kickoff  = new Date("2026-06-11T00:00:00");
  const final    = new Date("2026-07-20T00:00:00");
  const now      = new Date();
  if (now >= final)    return t("countdown.live");
  if (now >= kickoff)  return t("countdown.live");
  const days = Math.ceil((kickoff - now) / 86400000);
  if (days === 0)      return t("countdown.today");
  return `⏳ ${days} ${t("countdown.days")}`;
}

function renderCountdown() {
  document.querySelectorAll(".wc-countdown").forEach(el => {
    el.textContent = getCountdownText();
  });
}

// ── Footer ────────────────────────────────────────────────────────────────────
function renderFooter() {
  const existing = document.getElementById("wc-footer");
  if (existing) existing.remove();
  const lang = window.LANG;
  document.body.insertAdjacentHTML("beforeend", `
    <footer id="wc-footer" class="bg-dark text-white text-center py-3 mt-5 small">
      <p class="mb-1 fw-bold">⚽ Quiniela Mundial 2026 <span class="badge bg-warning text-dark ms-1">v1.0 Beta</span></p>
      <p class="mb-0 text-secondary">
        ${lang === "en" ? "Organized by" : "Organizado por"}:
        <strong class="text-white">Ricardo Millán</strong> &nbsp;·&nbsp;
        <a href="mailto:millan.ricardo@gmail.com" class="text-secondary">millan.ricardo@gmail.com</a>
        &nbsp;·&nbsp; 281-730-9726
      </p>
    </footer>`);
}

document.addEventListener("DOMContentLoaded", () => {
  applyTranslations();
  renderCountdown();
  renderFooter();
  document.querySelectorAll(".lang-btn").forEach(b => {
    b.textContent = window.LANG === "es" ? "🇺🇸 EN" : "🇲🇽 ES";
    b.addEventListener("click", toggleLanguage);
  });
});

// Re-render footer when language changes
document.addEventListener("langchange", () => {
  renderCountdown();
  renderFooter();
});
