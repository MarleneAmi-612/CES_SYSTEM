// static/js/solicitudes.js

// ============== Meta helpers (CSRF + endpoint) ==============
function getMeta(name) {
  const el = document.querySelector(`meta[name="${name}"]`);
  return el ? el.content : "";
}
const csrfToken = getMeta("csrf-token");
const UPDATE_URL = getMeta("requests-update-url") || "/administracion/solicitudes/estado/";

// ============== Toasts (notificaciones) ==============
const TOAST_ICONS = { success: "✅", warn: "⚠️", error: "⛔", info: "ℹ️" };

function notify(message, type = "info", { timeout = 2800 } = {}) {
  const root = document.getElementById("toast-root");
  if (!root) return alert(message); // fallback

  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `
    <div class="t-ic" aria-hidden="true">${TOAST_ICONS[type] || "ℹ️"}</div>
    <div class="t-msg">${message}</div>
    <div class="t-close" title="Cerrar">×</div>
  `;

  const remove = () => {
    el.style.animation = "toast-out .18s ease-in forwards";
    setTimeout(() => el.remove(), 180);
  };

  el.querySelector(".t-close").addEventListener("click", remove);

  // Pausar autodescarga al pasar el mouse
  let timer = setTimeout(remove, timeout);
  el.addEventListener("mouseenter", () => clearTimeout(timer));
  el.addEventListener("mouseleave", () => (timer = setTimeout(remove, timeout)));

  root.appendChild(el);
}

// ============== Etiquetas y mensajes ==============
const LABEL_ES = {
  pending: "Pendiente",
  review: "Revisión",
  accepted: "Aprobada",
  rejected: "Rechazada",
  generating: "Generando",
  emailed: "Enviado por correo",
  downloaded: "Descargado por el alumno",
};

const ACTION_MSG = {
  to_review: 'Marcado como "Revisión".',
  approve: "Solicitud aprobada.",
  reject: "Solicitud rechazada.",
  generating: 'Marcado como "Generando".',
};

const ACTION_TYPE = { to_review: "warn", approve: "success", reject: "error", generating: "info" };

// ============== Collapse ==============
window.toggleCollapse = function (hd) {
  const bd = hd.nextElementSibling;
  const open = !bd.classList.contains("hide");
  bd.classList.toggle("hide", open);
  hd.setAttribute("aria-expanded", String(!open));
};

// ============== Modal helpers ==============
function openModal(sel) { const el = document.querySelector(sel); if (el) el.classList.add("is-open"); }
function closeModal(sel){ const el = document.querySelector(sel); if (el) el.classList.remove("is-open"); }

document.addEventListener("click", (e) => {
  const closer = e.target.closest("[data-close]");
  if (closer) closeModal(closer.getAttribute("data-close"));
});

// ============== Click de acciones ==============
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".a-btn");
  if (!btn) return;
  const id = btn.dataset.id;
  const action = btn.dataset.action;

  if (action === "reject") {
    document.getElementById("rej_id").value = id;
    document.getElementById("rej_reason").value = "";
    openModal("#rejectModal");
    return;
  }
  doUpdate(btn, id, action);
});

// ============== Llamada AJAX ==============
async function doUpdate(btn, id, action, extra = {}) {
  try {
    btn && (btn.disabled = true);

    if (!csrfToken) {
      notify("No se encontró el token CSRF. Recarga la página (Ctrl+F5).", "error");
      return;
    }

    const r = await fetch(UPDATE_URL, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      body: new URLSearchParams({ id, action, ...extra }),
    });

    const j = await r.json().catch(() => ({}));

    if (!r.ok || !j.ok) {
      notify(j.msg || "No se pudo actualizar.", "error");
      return;
    }

    // Actualiza chip en la fila
    const row = document.getElementById("row-" + id);
    if (row) {
      const chip = row.querySelector(".status-chip");
      chip.className = "status-chip " + j.new_status;
      chip.textContent = LABEL_ES[j.new_status] || j.new_status;
    }

    // Toast bonito
    notify(ACTION_MSG[action] || "Actualizado.", ACTION_TYPE[action] || "info");
    closeModal("#rejectModal");
  } catch (err) {
    console.error(err);
    notify("Error de red. Inténtalo de nuevo.", "error");
  } finally {
    btn && (btn.disabled = false);
  }
}

// ============== Submit del modal "Rechazar" ==============
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("rejectForm");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const id = document.getElementById("rej_id").value;
    const reason = document.getElementById("rej_reason").value.trim();
    if (!reason) return;
    const fakeBtn = document.querySelector(`#row-${id} [data-action="reject"]`);
    doUpdate(fakeBtn, id, "reject", { reason });
  });
});
