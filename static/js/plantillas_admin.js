/* ===========================================================
   Plantillas Admin — Importar documentos + miniaturas + modal
   =========================================================== */
"use strict";

const $  = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));

/* ---------- Miniaturas desde json_active ---------- */
function drawTemplate(canvas, data, title) {
  if (!canvas || !data) return;
  const ctx = canvas.getContext("2d");

  const page = (data.pages && data.pages[0]) || {
    width: 1280,
    height: 720,
    background: "#0b1120",
    layers: []
  };

  const container = canvas.parentElement;
  const targetW = Math.max(160, Math.min(200, (container?.clientWidth || 180)));
  const W = (canvas.width  = targetW);
  const H = (canvas.height = Math.round(targetW * (page.height / page.width)));

  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, W, H);

  const margin = 10;
  const sheetX = margin;
  const sheetY = margin;
  const sheetW = W - margin * 2;
  const sheetH = H - margin * 2;

  ctx.fillStyle = page.background || "#0f172a";
  ctx.fillRect(sheetX, sheetY, sheetW, sheetH);

  const s       = sheetW / page.width;
  const offsetX = sheetX;
  const offsetY = sheetY;

  const layers        = Array.isArray(page.layers) ? page.layers : [];
  const hasImageLayer = layers.some(l => l.type === "image" && l.url);

  if (hasImageLayer) {
    layers.slice(0, 120).forEach(l => {
      if (l.type === "rect") {
        ctx.fillStyle = l.fill || "#0f172a";
        ctx.fillRect(
          offsetX + (l.x || 0) * s,
          offsetY + (l.y || 0) * s,
          (l.w || 0) * s,
          (l.h || 0) * s
        );
      } else if (l.type === "text") {
        const fs = Math.max(8, (l.fontSize || 18) * s);
        ctx.fillStyle = l.fill || "#e5e7eb";
        ctx.font = `600 ${fs}px system-ui, -apple-system, Segoe UI, Roboto, sans-serif`;
        const txt = String(l.text || "").replace(/\{\{.*?\}\}/g, "▢");
        const x   = offsetX + (l.x || 0) * s;
        const y   = offsetY + (l.y || 0) * s + fs;
        if (l.maxWidth) ctx.fillText(txt, x, y, (l.maxWidth || 0) * s);
        else            ctx.fillText(txt, x, y);
      } else if (l.type === "image" && l.url) {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
          const w = (l.w || img.naturalWidth)  * s;
          const h = (l.h || img.naturalHeight) * s;
          ctx.drawImage(
            img,
            offsetX + (l.x || 0) * s,
            offsetY + (l.y || 0) * s,
            w,
            h
          );
        };
        img.src = l.url;
      }
    });
  } else {
    const iconW = sheetW * 0.55;
    const iconH = sheetH * 0.65;
    const iconX = sheetX + (sheetW - iconW) / 2;
    const iconY = sheetY + (sheetH - iconH) / 2 - 6;

    ctx.fillStyle = "#0b1120";
    ctx.beginPath();
    ctx.moveTo(iconX, iconY);
    ctx.lineTo(iconX + iconW, iconY);
    ctx.lineTo(iconX + iconW, iconY + iconH);
    ctx.lineTo(iconX, iconY + iconH);
    ctx.closePath();
    ctx.fill();

    const foldSize = iconW * 0.22;
    ctx.fillStyle = "#111827";
    ctx.beginPath();
    ctx.moveTo(iconX + iconW, iconY);
    ctx.lineTo(iconX + iconW - foldSize, iconY);
    ctx.lineTo(iconX + iconW, iconY + foldSize);
    ctx.closePath();
    ctx.fill();

    const lineMarginX = iconW * 0.15;
    const lineStartX  = iconX + lineMarginX;
    const lineEndX    = iconX + iconW - lineMarginX;
    let lineY         = iconY + iconH * 0.35;
    const lineGap     = iconH * 0.09;

    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth   = 2;
    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.moveTo(lineStartX, lineY);
      ctx.lineTo(lineEndX, lineY);
      ctx.stroke();
      lineY += lineGap;
    }

    let ext = "";
    if (typeof title === "string") {
      const m = title.match(/\.([a-z0-9]+)$/i);
      if (m) ext = m[1].toUpperCase();
    }
    if (!ext) ext = "DOC";

    ctx.fillStyle = "#f97316";
    ctx.font = `700 ${Math.max(14, sheetW * 0.13)}px system-ui, -apple-system, Segoe UI, Roboto, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(ext, iconX + iconW / 2, iconY + iconH * 0.78);
  }
}

function renderAllThumbnails() {
  $$(".card--tpl").forEach(card => {
    const img    = card.querySelector(".thumb__img");
    const canvas = card.querySelector("canvas.tpl");
    if (img || !canvas) return;

    try {
      const raw  = card.getAttribute("data-json") || "{}";
      const data = JSON.parse(raw);
      drawTemplate(canvas, data);
    } catch (e) {}
  });
}

let _rszT;
function bindResizeRerender() {
  window.addEventListener("resize", () => {
    clearTimeout(_rszT);
    _rszT = setTimeout(renderAllThumbnails, 120);
  });
}

/* ---------- Filtros ---------- */
function activeKind() {
  const chip = $("#kind-filter .chip.is-active");
  return chip ? (chip.getAttribute("data-kind") || "").toLowerCase() : "";
}

function applyFilter() {
  const q = ($("#tpl-search")?.value || "").trim().toLowerCase();
  const k = activeKind(); // "", "design", "cproem", "dc3"

  $$(".card--tpl, .card--tpl-docx").forEach(card => {
    const title   = (card.getAttribute("data-title") || "").toLowerCase();
    const kindRaw = (card.getAttribute("data-kind")  || "").toLowerCase();

    const okQ = !q || title.includes(q) || kindRaw.includes(q);

    // ---- aquí está el truco del filtro de Diplomas ----
    let okK = true;
    if (k) {
      if (k === "design") {
        // Chip "Diplomas": mostrar tanto diseños como DOCX de tipo diploma
        okK = (kindRaw === "design" || kindRaw === "diploma");
      } else {
        okK = (kindRaw === k);
      }
    }

    card.style.display = (okQ && okK) ? "" : "none";
  });
}

function initFilters() {
  $$("#kind-filter .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      $$("#kind-filter .chip").forEach(c => c.classList.remove("is-active"));
      chip.classList.add("is-active");
      applyFilter();
    });
  });

  $("#tpl-search")?.addEventListener("input", applyFilter);

  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !/input|textarea/i.test(e.target.tagName)) {
      e.preventDefault();
      $("#tpl-search")?.focus();
    }
  });
}

/* ---------- Importar documentos + modal de modos ---------- */
function initImport() {
  const btnImport   = $("#btnImport");
  const fileDesign  = $("#importFile");
  const formDesign  = $("#importForm");
  const fileDocx    = $("#importDocxTplFile");
  const formDocx    = $("#importDocxTplForm");

  const modal       = $("#importModeModal");
  const btnDesign   = $("#importModeDesign");
  const btnDocxMode = $("#importModeDocxTpl");
  const backdrop    = modal ? modal.querySelector(".c-modal__backdrop") : null;
  const cancelBtn   = modal ? modal.querySelector("[data-import-cancel]") : null;

  function openModal() {
    if (!modal) return;
    modal.classList.add("is-open");
    modal.removeAttribute("aria-hidden");
    modal.dataset.open = "1";
    const firstBtn = modal.querySelector(".import-mode__option");
    if (firstBtn) firstBtn.focus();
  }

  function closeModal() {
    if (!modal) return;
    if (btnImport) btnImport.focus(); // saca el focus antes de aria-hidden
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    delete modal.dataset.open;
  }

  if (btnImport && modal) {
    btnImport.addEventListener("click", function (e) {
      e.preventDefault();
      openModal();
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeModal);
  }
  if (cancelBtn) {
    cancelBtn.addEventListener("click", closeModal);
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal && modal.dataset.open === "1") {
      closeModal();
    }
  });

  // Diseño / imagen de fondo
  if (btnDesign && fileDesign && formDesign) {
    btnDesign.addEventListener("click", function () {
      closeModal();
      fileDesign.click();
    });
    fileDesign.addEventListener("change", function () {
      if (!fileDesign.files || !fileDesign.files.length) return;
      formDesign.submit();
    });
  }

  // Plantilla DOCX con variables
  if (btnDocxMode && fileDocx && formDocx) {
    btnDocxMode.addEventListener("click", function () {
      closeModal();
      fileDocx.click();
    });
    fileDocx.addEventListener("change", function () {
      if (!fileDocx.files || !fileDocx.files.length) return;
      formDocx.submit();
    });
  }
}

/* ---------- Confirmar eliminación con modal bonito ---------- */
function initConfirm() {
  const modal    = document.getElementById("confirmModal");
  const textEl   = document.getElementById("confirmText");
  const btnOk    = document.getElementById("confirmOk");
  const btnCancel= document.getElementById("confirmCancel");
  const backdrop = modal ? modal.querySelector(".c-modal__backdrop") : null;

  if (!modal || !btnOk || !btnCancel || !backdrop) {
    document.addEventListener("submit", function (ev) {
      const form = ev.target;
      if (!form || !form.classList || !form.classList.contains("js-confirm")) return;
      const msg = form.getAttribute("data-confirm") || "¿Confirmas la acción?";
      if (!window.confirm(msg)) ev.preventDefault();
    });
    return;
  }

  let pendingForm = null;

  function openModal(message, form) {
    pendingForm = form;
    if (textEl) textEl.textContent = message;
    modal.classList.add("is-open");
    modal.removeAttribute("aria-hidden");
  }

  function closeModal() {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    pendingForm = null;
  }

  btnCancel.addEventListener("click", function () {
    closeModal();
  });

  backdrop.addEventListener("click", function () {
    closeModal();
  });

  btnOk.addEventListener("click", function () {
    if (pendingForm) {
      const f = pendingForm;
      pendingForm = null;
      closeModal();
      f.submit();
    } else {
      closeModal();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal.classList.contains("is-open")) {
      closeModal();
    }
  });

  document.addEventListener("submit", function (ev) {
    const form = ev.target;
    if (!form || !form.classList || !form.classList.contains("js-confirm")) return;

    ev.preventDefault();
    const msg = form.getAttribute("data-confirm") || "¿Confirmas la acción?";
    openModal(msg, form);
  });
}

/* ---------- Init global ---------- */
document.addEventListener("DOMContentLoaded", () => {
  renderAllThumbnails();
  bindResizeRerender();
  initFilters();
  applyFilter();
  initImport();
  initConfirm();
});

// segunda versión de renderAllThumbnails (compatibilidad)
function renderAllThumbnails() {
  $$(".card--tpl").forEach(card => {
    const img    = card.querySelector(".thumb__img");
    const canvas = card.querySelector("canvas.tpl");
    if (img || !canvas) return;

    const title = card.getAttribute("data-title") || "";
    let data    = {};

    try {
      const raw = card.getAttribute("data-json");
      if (raw && raw.trim() !== "") {
        data = JSON.parse(raw);
      }
    } catch (e) {
      data = {};
    }

    drawTemplate(canvas, data, title);
  });
}

/* ---------- Dropdown DOCX custom ---------- */
document.addEventListener("DOMContentLoaded", function () {
  const docxSelect = document.getElementById("docxSelect");
  const hiddenTipo = document.getElementById("docxTplTipo");
  const labelSpan = document.getElementById("docxSelectLabel");

  if (!docxSelect || !hiddenTipo || !labelSpan) return;

  const trigger = docxSelect.querySelector(".docx-select__trigger");
  const options = Array.from(docxSelect.querySelectorAll(".docx-select__option"));

  // abrir/cerrar menú
  trigger.addEventListener("click", () => {
    const isOpen = docxSelect.classList.toggle("is-open");
    trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });

  // seleccionar opción
  options.forEach((opt) => {
    opt.addEventListener("click", () => {
      const value = opt.dataset.value;
      const text = opt.textContent.trim();

      hiddenTipo.value = value;
      labelSpan.textContent = text;

      options.forEach(o => o.classList.remove("is-active"));
      opt.classList.add("is-active");

      docxSelect.classList.remove("is-open");
      trigger.setAttribute("aria-expanded", "false");
    });
  });

  // cerrar al hacer click fuera
  document.addEventListener("click", (ev) => {
    if (!docxSelect.contains(ev.target)) {
      docxSelect.classList.remove("is-open");
      trigger.setAttribute("aria-expanded", "false");
    }
  });
});
