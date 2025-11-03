/* ===========================================================
   Plantillas Admin — sin JSON visible, con Importar documentos
   =========================================================== */
"use strict";

const $  = (s, c=document)=>c.querySelector(s);
const $$ = (s, c=document)=>Array.from(c.querySelectorAll(s));

/* ---------- Miniaturas desde json_active ---------- */
function drawTemplate(canvas, data){
  if (!canvas || !data) return;
  const ctx  = canvas.getContext("2d");
  const page = (data.pages && data.pages[0]) || {width:1280, height:720, background:"#fff", layers:[]};

  const container = canvas.parentElement;
  const targetW = Math.max(160, Math.min(200, (container?.clientWidth || 180)));
  const W = canvas.width  = targetW;
  const H = canvas.height = Math.round(targetW * (page.height / page.width));

  ctx.fillStyle = page.background || "#fff";
  ctx.fillRect(0, 0, W, H);

  const s = W / page.width;

  (page.layers || []).slice(0, 120).forEach(l=>{
    if (l.type === "rect"){
      ctx.fillStyle = l.fill || "#e5e7eb";
      ctx.fillRect((l.x||0)*s, (l.y||0)*s, (l.w||0)*s, (l.h||0)*s);
    } else if (l.type === "text"){
      const fs = Math.max(8, (l.fontSize||18) * s);
      ctx.fillStyle = l.fill || "#111";
      ctx.font = `600 ${fs}px system-ui, -apple-system, Segoe UI, Roboto, sans-serif`;
      const txt = String(l.text||"").replace(/\{\{.*?\}\}/g, "▢");
      const x = (l.x||0)*s, y = (l.y||0)*s + fs;
      if (l.maxWidth) ctx.fillText(txt, x, y, (l.maxWidth||0)*s);
      else ctx.fillText(txt, x, y);
    } else if (l.type === "image" && l.url){
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = ()=>{
        const w = (l.w || img.naturalWidth)  * s;
        const h = (l.h || img.naturalHeight) * s;
        ctx.drawImage(img, (l.x||0)*s, (l.y||0)*s, w, h);
      };
      img.src = l.url;
    }
  });
}

function renderAllThumbnails(){
  $$(".card--tpl").forEach(card=>{
    const img = card.querySelector(".thumb__img");
    const canvas = card.querySelector("canvas.tpl");
    if (img || !canvas) return;
    try {
      const raw = card.getAttribute("data-json") || "{}";
      const data = JSON.parse(raw);
      drawTemplate(canvas, data);
    } catch(_) {}
  });
}

let _rszT;
function bindResizeRerender(){
  window.addEventListener("resize", ()=>{
    clearTimeout(_rszT);
    _rszT = setTimeout(renderAllThumbnails, 120);
  });
}

/* ---------- Filtros ---------- */
function activeKind(){
  const chip = $("#kind-filter .chip.is-active");
  return chip ? (chip.getAttribute("data-kind") || "").toLowerCase() : "";
}
function applyFilter(){
  const q = ($("#tpl-search")?.value || "").trim().toLowerCase();
  const k = activeKind();
  $$(".card--tpl").forEach(card=>{
    const title = (card.getAttribute("data-title") || "").toLowerCase();
    const kind  = (card.getAttribute("data-kind")  || "").toLowerCase();
    const okQ   = !q || title.includes(q) || kind.includes(q);
    const okK   = !k || kind === k;
    card.style.display = (okQ && okK) ? "" : "none";
  });
}
function initFilters(){
  $$("#kind-filter .chip").forEach(chip=>{
    chip.addEventListener("click", ()=>{
      $$("#kind-filter .chip").forEach(c=>c.classList.remove("is-active"));
      chip.classList.add("is-active");
      applyFilter();
    });
  });
  $("#tpl-search")?.addEventListener("input", applyFilter);
  document.addEventListener("keydown", (e)=>{
    if (e.key === "/" && !/input|textarea/i.test(e.target.tagName)){
      e.preventDefault(); $("#tpl-search")?.focus();
    }
  });
}

/* ---------- Confirm modal para eliminar ---------- */
(function(){
  const modal = $("#confirmModal");
  if (!modal) return;

  let pendingForm = null;
  document.body.addEventListener("submit", ev=>{
    const form = ev.target.closest("form.js-confirm");
    if (!form) return;
    ev.preventDefault();
    pendingForm = form;
    const msg = form.getAttribute("data-confirm") || "¿Confirmas la acción?";
    $("#confirmMsg").textContent = msg;
    modal.setAttribute("aria-hidden", "false");
    modal.classList.add("open");
  });

  $("#confirmCancel")?.addEventListener("click", ()=>{
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    pendingForm = null;
  });
  $("#confirmOk")?.addEventListener("click", ()=>{
    if (pendingForm) pendingForm.submit();
    pendingForm = null;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
  });
  $(".modal__overlay")?.addEventListener("click", ()=>{
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    pendingForm = null;
  });
})();

/* ---------- Importar documentos (PDF/DOCX/PPTX/Imágenes) ---------- */
function initImport(){
  const btn  = $("#btnImport");
  const file = $("#importFile");
  const form = $("#importForm");
  if (!btn || !file || !form) return;

  btn.addEventListener("click", ()=> file.click());
  file.addEventListener("change", ()=>{
    if (!file.files || !file.files.length) return;
    form.submit(); // POST a plantilla_import
  });
}

/* ---------- Init ---------- */
document.addEventListener("DOMContentLoaded", ()=>{
  renderAllThumbnails();
  bindResizeRerender();
  initFilters();
  applyFilter();
  initImport();
});
