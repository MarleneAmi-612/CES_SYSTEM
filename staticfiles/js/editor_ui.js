/* ===========================================================
   Editor CES — UI (Ribbon)  v6.3  (IDs -> data-role para snap)
   =========================================================== */
"use strict";

/* Tabs */
document.addEventListener("DOMContentLoaded", () => {
  const tabs  = Array.from(document.querySelectorAll(".ribbon .tab"));
  const pages = Array.from(document.querySelectorAll(".ribbon .ribbon-page"));
  const activateTab = (name)=>{
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === name));
    pages.forEach(p => p.classList.toggle("active", p.dataset.tab === name));
  };
  tabs.forEach(t => t.addEventListener("click", () => activateTab(t.dataset.tab)));
  const already = tabs.find(t => t.classList.contains("active"));
  if (!already && tabs.length) activateTab(tabs[0].dataset.tab || "");
});

/* Bind núcleo */
document.addEventListener("editor-ready", bindAll);
if (window.Editor) setTimeout(bindAll, 0);

function bindAll(){
  const on     = (sel, ev, fn)=>{ const el=document.querySelector(sel); if (el) el.addEventListener(ev, fn); };
  const click  = (sel, fn)=> on(sel, "click", (e)=>{ e.preventDefault(); fn(e); });
  const change = (sel, fn)=> on(sel, "change", ()=>{ const el=document.querySelector(sel); fn(el); });

  // Topbar
  click("#btnSave", ()=>window.Editor?.saveJSON?.());

  // Inicio
  click("#undo",       ()=>window.Editor?.undo?.());
  click("#redo",       ()=>window.Editor?.redo?.());
  click("#duplicate",  ()=>window.Editor?.duplicate?.());
  click("#delete",     ()=>window.Editor?.removeSelection?.());
  click("#save",       ()=>window.Editor?.saveJSON?.());

  // Texto / estilo
  change("#fontFamily", (el)=>window.Editor?.applyFontFamily?.(el.value));
  change("#fontSize",   (el)=>window.Editor?.applyFontSize?.(el.value));
  click("#bold",        ()=>window.Editor?.toggleBold?.());
  click("#italic",      ()=>window.Editor?.toggleItalic?.());
  click("#underline",   ()=>window.Editor?.toggleUnderline?.());
  change("#fillColor",  (el)=>window.Editor?.setFillColor?.(el.value));
  change("#strokeColor",(el)=>window.Editor?.setStroke?.(el.value));
  change("#strokeWidth",(el)=>window.Editor?.setStrokeWidth?.(+el.value || 1));
  change("#opacity",    (el)=>window.Editor?.setOpacity?.(+el.value || 1));

  // Insertar
  click("#addText",   ()=>window.Editor?.addText?.());
  click("#addRect",   ()=>window.Editor?.addRect?.());
  click("#addCircle", ()=>window.Editor?.addCircle?.());
  click("#addLine",   ()=>window.Editor?.addLine?.());

  // Diseño
  change("#bgColor",  (el)=>window.Editor?.setFillColor?.(el.value));

  // Escuchar a TODOS los toggles declarados en el template por data-role
  document.querySelectorAll('[data-role="snap"]').forEach(el=>{
    el.addEventListener("change", ()=> window.Editor?.setSnap?.(!!el.checked));
  });
  document.querySelectorAll('[data-role="snapSize"]').forEach(el=>{
    el.addEventListener("change", ()=> window.Editor?.setSnapSize?.(+el.value || 10));
  });
  click("#toggleGrid",()=>window.Editor?.toggleGrid?.());

  // Formato
  click("#alignLeft",   ()=>window.Editor?.alignLeft?.());
  click("#alignCenter", ()=>window.Editor?.alignCenter?.());
  click("#alignRight",  ()=>window.Editor?.alignRight?.());
  click("#bringFront",  ()=>window.Editor?.bringFront?.());
  click("#sendBack",    ()=>window.Editor?.sendBack?.());
  click("#distributeH", ()=>window.Editor?.distributeH?.());
  click("#distributeV", ()=>window.Editor?.distributeV?.());

  // Vista
  click("#zoomOut",   ()=>window.Editor?.setZoom?.(getZoom()*0.9));
  click("#zoomIn",    ()=>window.Editor?.setZoom?.(getZoom()*1.1));
  click("#zoom100",   ()=>window.Editor?.setZoom?.(1));
  click("#zoomFit",   ()=>window.Editor?.fitToWidth?.());
  click("#zoomSel",   ()=>window.Editor?.zoomSelection?.());
  click("#centerSel", ()=>window.Editor?.centerSelection?.());

  // Export/Import
  click("#expPng",   ()=>window.Editor?.exportPNG?.(1));
  click("#expThumb", ()=>window.Editor?.exportThumbnail?.());
  click("#expSvg",   ()=>window.Editor?.exportSVG?.());
  click("#expJson",  ()=>window.Editor?.exportJSONFile?.());
  click("#impJson",  ()=>document.querySelector("#impJsonFile")?.click());
  change("#impJsonFile", (el)=>{ const f=el.files?.[0]; if (f) window.Editor?.importJSONFile?.(f); el.value=""; });

  // Atajos
  document.addEventListener("keydown", (e) => {
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "s") { e.preventDefault(); window.Editor?.saveJSON?.(); }
    if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) { e.preventDefault(); window.Editor?.undo?.(); }
    if ((mod && e.key.toLowerCase() === "y") || (mod && e.shiftKey && e.key.toLowerCase() === "z")) {
      e.preventDefault(); window.Editor?.redo?.();
    }
    if (e.key === "Delete") { e.preventDefault(); window.Editor?.removeSelection?.(); }
  });

  function getZoom(){
    const t = document.getElementById("zoomLabel")?.textContent || "100%";
    const n = parseInt(t,10);
    return isNaN(n)?1:n/100;
  }
}

/* Drawer abrir/cerrar */
document.addEventListener("DOMContentLoaded", () => {
  const btn    = document.getElementById("btnJsonToggle");
  const drawer = document.getElementById("drawer");
  const close  = document.getElementById("drawerClose");
  if (btn && drawer)   btn.addEventListener("click", () => drawer.classList.add("open"));
  if (close && drawer) close.addEventListener("click", () => drawer.classList.remove("open"));
});

/* Ajuste de alto del área canvas y fit (suave) */
(function () {
  let rafId = 0;
  function resizeCanvasArea() {
    const wrap   = document.getElementById("canvasWrap");
    const ribbon = document.querySelector(".ribbon");
    if (!wrap) return;
    const h = window.innerHeight - ((ribbon?.getBoundingClientRect().bottom || 0) + 24);
    wrap.style.height = Math.max(360, h) + "px";
    cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => window.Editor?.fitToWidth?.());
  }
  window.addEventListener("resize", resizeCanvasArea);
  document.addEventListener("DOMContentLoaded", resizeCanvasArea);
  document.addEventListener("editor-ready",   resizeCanvasArea);
})();

/* Quitar posibles rulers antiguos */
(() => {
  if (window.__hide_rulers_safe__) return; window.__hide_rulers_safe__ = true;
  const kill = ()=>document.querySelectorAll(".ruler,.ruler-x,.ruler-y").forEach(n=>n.remove());
  document.addEventListener("editor-ready", kill);
  setTimeout(kill, 0);
})();

/* Tamaño/Orientación + Zoom bar */
(() => {
  if (window.__orientation_zoom_ui_init__) return; window.__orientation_zoom_ui_init__ = true;

  const SIZE_HOSTS = [
    '.ribbon .ribbon-page[data-tab="disenio"] .group .group-content',
    '.ribbon .ribbon-page[data-tab="disenio"]',
    '.ribbon .ribbon-page[data-tab="formato"]'
  ];

  function createSizeGroup(){
    const g = document.createElement('div');
    g.id = 'size-controls';
    g.className = 'ribbon-group';
    // Fallback: solo se usa si no existe en el template
    g.innerHTML = `
      <div class="group-title">Tamaño</div>
      <div class="group-content">
        <button type="button" class="rbtn" id="btnPortrait">Vertical (Carta)</button>
        <button type="button" class="rbtn" id="btnLandscape">Horizontal (Carta)</button>
        <label class="switch ml-12">
          <input data-role="snap" type="checkbox" checked>
          <span>Snap</span>
        </label>
        <input data-role="snapSize" type="number" class="rinput w-72 ml-8" min="1" max="200" step="1" value="10" />
      </div>`;
    return g;
  }

  function bindSizeHandlers(scope=document){
    scope.querySelector('#btnPortrait') ?.addEventListener('click', ()=>{ window.Editor?.setOrientation?.('portrait');  window.Editor?.fitToWidth?.(); });
    scope.querySelector('#btnLandscape')?.addEventListener('click', ()=>{ window.Editor?.setOrientation?.('landscape'); window.Editor?.fitToWidth?.(); });

    // Bindeo por data-role dentro del scope del grupo
    scope.querySelectorAll('[data-role="snap"]').forEach(el=>{
      el.addEventListener('change', ()=> window.Editor?.setSnap?.(!!el.checked));
    });
    scope.querySelectorAll('[data-role="snapSize"]').forEach(el=>{
      el.addEventListener('change', ()=> window.Editor?.setSnapSize?.(+el.value || 10));
    });
  }

  function mountSizeControls(){
    // 🛡️ Si ya existen los controles en la plantilla, no montamos nada
    if (document.querySelector('[data-role="snap"], [data-role="snapSize"]')) {
      return true;
    }
    if (document.getElementById('size-controls')) return true;

    for (const sel of SIZE_HOSTS){
      const host = document.querySelector(sel);
      if (host){
        const g = createSizeGroup();
        host.appendChild(g);
        bindSizeHandlers(host);
        return true;
      }
    }
    return false;
  }

  function mountZoomBar(){
    if (document.getElementById('zoomBar')) return;
    const host =
      document.querySelector('.ribbon .ribbon-page[data-tab="vista"] .group .group-content') ||
      document.querySelector('.ribbon .ribbon-page[data-tab="vista"]') ||
      document.body;

    const bar = document.createElement('div');
    bar.id = 'zoomBar';
    bar.className = 'zoombar';
    bar.innerHTML = `
      <button class="rbtn" id="zoomMinus">−</button>
      <input id="zoomSlider" type="range" min="10" max="600" value="100" step="1" />
      <button class="rbtn" id="zoomPlus">+</button>
      <span id="zoomLabel" class="zoom-pct">100%</span>`;
    host.appendChild(bar);

    const slider = document.getElementById('zoomSlider');
    const minus  = document.getElementById('zoomMinus');
    const plus   = document.getElementById('zoomPlus');
    const label  = document.getElementById('zoomLabel');
    const setLbl = (z)=>{ if (label) label.textContent = `${Math.round(z*100)}%`; if (slider) slider.value = String(Math.round(z*100)); };

    slider?.addEventListener('input', ()=>{
      const pct = Math.max(10, Math.min(600, parseInt(slider.value||'100',10)));
      window.Editor?.setZoom?.(pct/100); setLbl(pct/100);
    });
    minus?.addEventListener('click', ()=>{
      const cur = parseInt(slider?.value||'100',10);
      const pct = Math.max(10, cur-10);
      window.Editor?.setZoom?.(pct/100); setLbl(pct/100);
    });
    plus ?.addEventListener('click', ()=>{
      const cur = parseInt(slider?.value||'100',10);
      const pct = Math.min(600, cur+10);
      window.Editor?.setZoom?.(pct/100); setLbl(pct/100);
    });
  }

  function init(){ mountSizeControls(); mountZoomBar(); }

  if (document.readyState==="loading"){
    document.addEventListener("DOMContentLoaded", init, { once:true });
  } else { init(); }
  document.addEventListener("editor-ready", init);
})();
