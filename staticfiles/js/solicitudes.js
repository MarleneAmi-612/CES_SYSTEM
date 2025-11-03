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
  if (!root) return alert(message); // Fallback

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

// ✅ Mensaje correcto para aprobación
const ACTION_MSG = {
  to_review: 'Marcado como "Revisión".',
  approve: "Solicitud aceptada correctamente, ahora podrá trabajar en su documento en el apartado de Egresados.",
  reject: "Solicitud rechazada.",
  generating: 'Marcado como "Generando".',
};

const ACTION_TYPE = { to_review: "warn", approve: "success", reject: "error", generating: "info" };

// ============== Modal helpers ==============
function openModal(sel) {
  const el = document.querySelector(sel);
  if (el) el.classList.add("is-open");
}
function closeModal(sel) {
  const el = document.querySelector(sel);
  if (el) el.classList.remove("is-open");
}

document.addEventListener("click", (e) => {
  const closer = e.target.closest("[data-close]");
  if (closer) closeModal(closer.getAttribute("data-close"));
});

// ============== Llamada AJAX ==============
async function doUpdate(btn, id, action, extra = {}) {
  try {
    if (btn) btn.disabled = true;

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
      if (chip) {
        chip.className = "status-chip " + j.new_status;
        chip.textContent = LABEL_ES[j.new_status] || j.new_status;
      }
    }

    // Si el modal de detalle está abierto, refresca el estado y motivo
    const detOpen = document.getElementById("detailModal");
    if (detOpen && detOpen.classList.contains("is-open")) {
      const st = document.getElementById("det_status");
      if (st) st.textContent = LABEL_ES[j.new_status] || j.new_status;
      const rr = document.getElementById("det_reason");
      if (rr) rr.textContent = (j.new_status === "rejected" ? (extra.reason || rr.textContent) : "—");
    }

    notify(ACTION_MSG[action] || "Actualizado.", ACTION_TYPE[action] || "info");
    closeModal("#rejectModal");
  } catch (err) {
    console.error(err);
    notify("Error de red. Inténtalo de nuevo.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ============== Clicks generales (acciones y ver detalle) ==============
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".a-btn, .a-btn.ghost");
  if (!btn) return;

  // Abrir modal de detalle
  if (btn.dataset.view === "detail") {
    const id = btn.dataset.id;
    document.getElementById("det_id").value = id;

    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val && String(val).trim() ? val : "—";
    };

    const fullName = [btn.dataset.name || "", btn.dataset.lastname || ""].join(" ").trim();
    set("det_name", fullName || "—");
    set("det_email", btn.dataset.email || "");
    set("det_program", btn.dataset.program || "");
    const period = [btn.dataset.start || "", btn.dataset.end || ""].filter(Boolean).join("  →  ");
    set("det_period", period || "—");
    set("det_curp", btn.dataset.curp || "");
    set("det_rfc", btn.dataset.rfc || "");
    set("det_job", btn.dataset.job_title || "");
    set("det_industry", btn.dataset.industry || "");
    set("det_status", LABEL_ES[btn.dataset.status] || btn.dataset.status || "—");
    set("det_reason", btn.dataset.reason || "");

    openModal("#detailModal");
    return;
  }

  // Acciones de estado
  const id = btn.dataset.id;
  const action = btn.dataset.action;

  if (action === "reject") {
    document.getElementById("rej_id").value = id;
    document.getElementById("rej_reason").value = "";
    openModal("#rejectModal");
    return;
  }

  // (Opcional) Confirmación de aprobar:
  // if (action === "approve") {
  //   if (!confirm("¿Deseas aceptar esta solicitud?")) return;
  // }

  doUpdate(btn, id, action);
});

// ============== Botones dentro del modal de detalle ==============
document.addEventListener("DOMContentLoaded", () => {
  const getDetId = () => document.getElementById("det_id").value;

  const bind = (sel, action, extra = {}) => {
    const b = document.getElementById(sel);
    if (!b) return;
    b.addEventListener("click", () => {
      const id = getDetId();
      if (!id) return;

      if (action === "reject") {
        document.getElementById("rej_id").value = id;
        document.getElementById("rej_reason").value = "";
        openModal("#rejectModal");
        return;
      }
      doUpdate(b, id, action, extra);
    });
  };

  bind("det_btn_review", "to_review");
  bind("det_btn_generating", "generating");
  bind("det_btn_approve", "approve");
  bind("det_btn_reject", "reject");
});

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
