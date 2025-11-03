/* ===========================================================
   Editor CES — Núcleo (FabricJS)  v6.3
   - Canvas, histórico (undo/redo), capas, zoom, orientación
   - Guardar JSON (POST)
   - Importar: imágenes, PDF (pdfjsLib), DOCX/PPTX/ODT/ODP (backend)
   - CSP-friendly: NO inyecta <style> ni handlers inline
   - Rendimiento: límite de resolución al rasterizar PDF, guards en fitToWidth
   =========================================================== */
"use strict";

(function () {
  // Utils
  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  // Estado base
  const DEFAULT_STATE = {
    pages: [{ width: 1280, height: 720, background: "#ffffff", layers: [] }],
  };

  // CSRF + fetch JSON
  function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
  }
  async function postJSON(url, data) {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify(data),
      credentials: "include",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  // Canvas / historial
  let canvas, _history = [], _redo = [];
  let _zoom = 1;
  let _snapOn = true;
  let _snapSize = 10;

  // --- helpers de eventos propios ---
  function emitSnapChange() {
    try {
      const ev = new CustomEvent("snap-changed", { detail: { on: !!_snapOn, size: _snapSize } });
      document.dispatchEvent(ev);
    } catch { /* noop en browsers antiguos */ }
  }

  const Editor = {
    // ciclo
    init, saveJSON,
    // selección / edición
    undo, redo, duplicate, removeSelection,
    applyFontFamily, applyFontSize, toggleBold, toggleItalic, toggleUnderline,
    setFillColor, setStroke, setStrokeWidth, setOpacity,
    addText, addRect, addCircle, addLine,
    alignLeft, alignCenter, alignRight, bringFront, sendBack,
    // vista
    setZoom, fitToWidth, toggleGrid, distributeH, distributeV,
    zoomSelection, centerSelection, setOrientation,
    // snap
    setSnap, setSnapSize,
    // ➕ getters para que la UI lea el estado actual
    getSnapSize, isSnapOn,
    // export
    exportPNG, exportThumbnail, exportSVG, exportJSONFile, importJSONFile,
    // importar local
    importLocalFile,
  };
  window.Editor = Editor;

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    // Cargar estado inicial
    let state = DEFAULT_STATE;
    try {
      const raw = $("#state")?.textContent || "{}";
      const parsed = JSON.parse(raw);
      if (parsed && parsed.pages?.length) state = parsed;
    } catch { /* noop */ }

    const page = state.pages[0];

    // Canvas
    // eslint-disable-next-line no-undef
    canvas = new fabric.Canvas("stage", {
      backgroundColor: page.background || "#ffffff",
      selection: true,
      preserveObjectStacking: true,
    });
    resizeCanvasToPage(page);
    loadLayersFromJSON(page.layers || []);

    // Snap visual al mover
    canvas.on("object:moving", e => {
      if (!_snapOn || !_snapSize) return;
      const o = e.target;
      if (!o) return;
      const step = _snapSize;
      o.set({
        left: Math.round((o.left || 0) / step) * step,
        top:  Math.round((o.top  || 0) / step) * step,
      });
    });

    // Historial
    _history = []; _redo = [];
    pushHistory();
    canvas.on("object:added",    pushHistoryDebounced);
    canvas.on("object:modified", pushHistoryDebounced);
    canvas.on("object:removed",  pushHistoryDebounced);

    // Importar
    bindImporter();

    // Listo: avisamos a la UI y emitimos el estado inicial de snap
    document.dispatchEvent(new Event("editor-ready"));
    emitSnapChange();

    // Primer ajuste de zoom en frame siguiente
    setTimeout(() => { try { fitToWidth(); } catch {} }, 0);
  }

  // ----- helpers de estado / página -----
  function currentPage() {
    const st = getState();
    if (!st.pages?.length) st.pages = JSON.parse(JSON.stringify(DEFAULT_STATE.pages));
    return st.pages[0];
  }
  function getState() {
    try {
      const raw = $("#state")?.textContent || "{}";
      const parsed = JSON.parse(raw);
      return parsed?.pages ? parsed : JSON.parse(JSON.stringify(DEFAULT_STATE));
    } catch {
      return JSON.parse(JSON.stringify(DEFAULT_STATE));
    }
  }
  function setState(newState) {
    const el = $("#state");
    if (el) el.textContent = JSON.stringify(newState || DEFAULT_STATE);
  }

  function resizeCanvasToPage(page) {
    if (!canvas) return;
    const W = page.width || 1280;
    const H = page.height || 720;
    canvas.setWidth(W);
    canvas.setHeight(H);
    canvas.renderAll();
  }

  function setOrientation(mode /* 'portrait' | 'landscape' */) {
    const page = currentPage();
    const isPortrait = (mode === "portrait");
    // Carta @300DPI aprox
    page.width  = isPortrait ? 2550 : 3300;
    page.height = isPortrait ? 3300 : 2550;
    resizeCanvasToPage(page);
    fitToWidth();
    pushHistory();
  }

  // ----- serialización -----
  function serializeLayersFromCanvas() {
    const objs = canvas.getObjects().map(objToLayer);
    const page = currentPage();
    page.background = canvas.backgroundColor || "#ffffff";
    page.layers = objs;
    const st = getState();
    st.pages[0] = page;
    return st;
  }

  function objToLayer(o) {
    if (!o) return null;
    if (o.type === "rect") {
      return {
        type: "rect",
        x: o.left || 0, y: o.top || 0,
        w: (o.width  || 0) * (o.scaleX || 1),
        h: (o.height || 0) * (o.scaleY || 1),
        fill: o.fill || "#111111",
        opacity: (o.opacity == null ? 1 : o.opacity),
      };
    }
    if (o.type === "circle") {
      const r = (o.radius || 0) * (o.scaleX || 1);
      return {
        type: "circle",
        x: o.left || 0, y: o.top || 0,
        r, fill: o.fill || "#111", opacity: (o.opacity == null ? 1 : o.opacity),
      };
    }
    if (o.type === "line") {
      const w = (o.width  || 0) * (o.scaleX || 1);
      const h = (o.height || 0) * (o.scaleY || 1);
      return {
        type: "rect", x: o.left || 0, y: o.top || 0,
        w: Math.max(1, w), h: Math.max(1, h),
        fill: o.stroke || "#111", opacity: (o.opacity == null ? 1 : o.opacity),
      };
    }
    if (o.type === "textbox" || o.type === "i-text" || o.type === "text") {
      return {
        type: "text",
        x: o.left || 0, y: o.top || 0,
        text: o.text || "", fontSize: o.fontSize || 28,
        fill: o.fill || "#111", opacity: (o.opacity == null ? 1 : o.opacity),
        fontFamily: o.fontFamily || "system-ui, Segoe UI, Roboto, sans-serif",
        fontWeight: o.fontWeight || "normal",
        fontStyle:  o.fontStyle  || "normal",
        underline:  !!o.underline,
      };
    }
    if (o.type === "image") {
      const url = o._originalElement?.src || o.src || "";
      return {
        type: "image",
        x: o.left || 0, y: o.top || 0,
        w: (o.width  || 0) * (o.scaleX || 1),
        h: (o.height || 0) * (o.scaleY || 1),
        url, opacity: (o.opacity == null ? 1 : o.opacity),
      };
    }
    return { type: "rect", x: 0, y: 0, w: 10, h: 10, fill: "#ccc" };
  }

  function loadLayersFromJSON(layers) {
    canvas.clear();
    canvas.backgroundColor = currentPage().background || "#ffffff";
    (layers || []).forEach((l) => {
      if (l.type === "rect") {
        // eslint-disable-next-line no-undef
        const r = new fabric.Rect({
          left: l.x || 0, top: l.y || 0, width: l.w || 0, height: l.h || 0,
          fill: l.fill || "#e5e7eb", opacity: (l.opacity == null ? 1 : l.opacity),
        });
        canvas.add(r);
      } else if (l.type === "circle") {
        // eslint-disable-next-line no-undef
        const c = new fabric.Circle({
          left: l.x || 0, top: l.y || 0, radius: l.r || 10,
          fill: l.fill || "#111", opacity: (l.opacity == null ? 1 : l.opacity),
        });
        canvas.add(c);
      } else if (l.type === "text") {
        // eslint-disable-next-line no-undef
        const t = new fabric.Textbox(l.text || "", {
          left: l.x || 0, top: l.y || 0,
          fontSize: l.fontSize || 28, fill: l.fill || "#111",
          fontFamily: l.fontFamily || "system-ui, Segoe UI, Roboto, sans-serif",
          fontWeight: l.fontWeight || "normal",
          fontStyle:  l.fontStyle  || "normal",
          underline:  !!l.underline,
          opacity: (l.opacity == null ? 1 : l.opacity),
        });
        canvas.add(t);
      } else if (l.type === "image" && l.url) {
        // eslint-disable-next-line no-undef
        fabric.Image.fromURL(l.url, (img) => {
          if (!img) return;
          const w = l.w || img.width, h = l.h || img.height;
          img.set({
            left: l.x || 0, top: l.y || 0,
            scaleX: (w / img.width), scaleY: (h / img.height),
            opacity: (l.opacity == null ? 1 : l.opacity),
          });
          canvas.add(img);
          canvas.renderAll();
        }, { crossOrigin: "anonymous" });
      }
    });
    canvas.renderAll();
  }

  // ----- historial -----
  let _histT;
  function pushHistoryDebounced() {
    clearTimeout(_histT);
    _histT = setTimeout(pushHistory, 150);
  }
  function pushHistory() {
    const json = canvas.toDatalessJSON();
    _history.push(JSON.stringify(json));
    if (_history.length > 100) _history.shift();
    _redo = [];
    setStatus("Listo");
  }
  function undo() {
    if (_history.length <= 1) return;
    const cur = _history.pop();
    _redo.push(cur);
    const prev = _history[_history.length - 1];
    canvas.loadFromJSON(JSON.parse(prev), () => canvas.renderAll());
    setStatus("↶ Deshacer");
  }
  function redo() {
    const next = _redo.pop();
    if (!next) return;
    _history.push(next);
    canvas.loadFromJSON(JSON.parse(next), () => canvas.renderAll());
    setStatus("↷ Rehacer");
  }

  // ----- edición -----
  function duplicate() {
    const sel = canvas.getActiveObject();
    if (!sel) return;
    sel.clone((cl) => {
      cl.set({ left: (sel.left || 0) + 16, top: (sel.top || 0) + 16 });
      canvas.add(cl).setActiveObject(cl);
      canvas.requestRenderAll();
      setTimeout(pushHistoryDebounced, 0);
    });
  }
  function removeSelection() {
    const sel = canvas.getActiveObjects();
    sel.forEach(o => canvas.remove(o));
    canvas.discardActiveObject();
    canvas.renderAll(); pushHistoryDebounced();
  }

  function applyFontFamily(v) { const o = canvas.getActiveObject(); if (o?.set) { o.set("fontFamily", v); canvas.renderAll(); pushHistoryDebounced(); } }
  function applyFontSize(v)   { const o = canvas.getActiveObject(); const n = parseInt(v, 10); if (o?.set && !isNaN(n)) { o.set("fontSize", n); canvas.renderAll(); pushHistoryDebounced(); } }
  function toggleBold()       { const o = canvas.getActiveObject(); if (o?.set) { o.set("fontWeight", o.fontWeight === "bold" ? "normal" : "bold"); canvas.renderAll(); pushHistoryDebounced(); } }
  function toggleItalic()     { const o = canvas.getActiveObject(); if (o?.set) { o.set("fontStyle", o.fontStyle === "italic" ? "normal" : "italic"); canvas.renderAll(); pushHistoryDebounced(); } }
  function toggleUnderline()  { const o = canvas.getActiveObject(); if (o?.set) { o.set("underline", !o.underline); canvas.renderAll(); pushHistoryDebounced(); } }
  function setFillColor(v)    {
    const o = canvas.getActiveObject();
    if (o?.set) { o.set("fill", v); canvas.renderAll(); pushHistoryDebounced(); }
    else { canvas.setBackgroundColor(v, () => canvas.renderAll()); pushHistoryDebounced(); }
  }
  function setStroke(v)       { const o = canvas.getActiveObject(); if (o?.set) { o.set("stroke", v); canvas.renderAll(); pushHistoryDebounced(); } }
  function setStrokeWidth(n)  { const o = canvas.getActiveObject(); if (o?.set) { o.set("strokeWidth", n); canvas.renderAll(); pushHistoryDebounced(); } }
  function setOpacity(n)      { const o = canvas.getActiveObject(); if (o?.set) { o.set("opacity", Math.max(0, Math.min(1, n))); canvas.renderAll(); pushHistoryDebounced(); } }

  // eslint-disable-next-line no-undef
  function addText()   { const t = new fabric.Textbox("Texto", { left: 80, top: 80, fontSize: 28, fill: "#111" }); canvas.add(t).setActiveObject(t); canvas.renderAll(); pushHistoryDebounced(); }
  // eslint-disable-next-line no-undef
  function addRect()   { const r = new fabric.Rect({ left: 120, top: 120, width: 240, height: 120, fill: "#e5e7eb" }); canvas.add(r).setActiveObject(r); canvas.renderAll(); pushHistoryDebounced(); }
  // eslint-disable-next-line no-undef
  function addCircle() { const c = new fabric.Circle({ left: 160, top: 160, radius: 64, fill: "#111" }); canvas.add(c).setActiveObject(c); canvas.renderAll(); pushHistoryDebounced(); }
  // eslint-disable-next-line no-undef
  function addLine()   { const l = new fabric.Rect({ left: 100, top: 200, width: 300, height: 3, fill: "#111" }); canvas.add(l).setActiveObject(l); canvas.renderAll(); pushHistoryDebounced(); }

  function alignLeft()   { const o = canvas.getActiveObject(); if (!o) return; o.set({ left: 0 }); canvas.renderAll(); pushHistoryDebounced(); }
  function alignCenter() { const o = canvas.getActiveObject(); if (!o) return; o.set({ left: (canvas.width - o.getScaledWidth()) / 2 }); canvas.renderAll(); pushHistoryDebounced(); }
  function alignRight()  { const o = canvas.getActiveObject(); if (!o) return; o.set({ left: (canvas.width - o.getScaledWidth()) }); canvas.renderAll(); pushHistoryDebounced(); }
  function bringFront()  { const o = canvas.getActiveObject(); if (!o) return; canvas.bringToFront(o); canvas.renderAll(); pushHistoryDebounced(); }
  function sendBack()    { const o = canvas.getActiveObject(); if (!o) return; canvas.sendToBack(o); canvas.renderAll(); pushHistoryDebounced(); }

  // ----- snap -----
  function setSnap(on)       { _snapOn   = !!on; emitSnapChange(); }
  function setSnapSize(size) { _snapSize = Math.max(1, +size || 10); emitSnapChange(); }
  function getSnapSize()     { return _snapSize; }
  function isSnapOn()        { return !!_snapOn; }

  // ----- vista / zoom -----
  function setZoom(z) {
    if (!canvas) return;
    _zoom = Math.max(0.1, Math.min(6, z || 1));
    const vp = canvas.viewportTransform || // eslint-disable-next-line no-undef
               fabric.iMatrix.concat();
    vp[0] = _zoom; vp[3] = _zoom;
    canvas.setViewportTransform(vp);
    updateZoomLabel();
  }
  function updateZoomLabel() {
    const label = $("#zoomLabel");
    if (label) label.textContent = `${Math.round(_zoom * 100)}%`;
  }
  function fitToWidth() {
    const wrap = $("#canvasWrap");
    if (!wrap || !canvas || !(canvas.width > 0)) return;
    const pad = 32;
    const cw = wrap.clientWidth || 0;
    const W = Math.max(100, cw - pad);
    const z = Math.max(0.1, Math.min(6, W / (canvas.width || 1)));
    setZoom(z);
  }
  function toggleGrid() {/* opcional */ }
  function distributeH() {/* opcional */ }
  function distributeV() {/* opcional */ }
  function zoomSelection() {
    const o = canvas.getActiveObject(); if (!o) return;
    const w = o.getScaledWidth(), wrapW = $("#canvasWrap")?.clientWidth || w;
    if (w > 0) setZoom(Math.max(0.1, Math.min(6, (wrapW - 48) / w)));
  }
  function centerSelection() { const o = canvas.getActiveObject(); if (!o) return; o.center(); canvas.renderAll(); }

  // ----- guardar -----
  async function saveJSON() {
    try {
      setStatus("Guardando…");
      const st = serializeLayersFromCanvas();
      setState(st);
      await postJSON(window.location.href, st);
      setStatus("✅ Guardado");
    } catch (e) {
      console.error(e);
      setStatus("⚠️ Error al guardar");
    }
  }

  // ----- export -----
  function exportPNG(scale = 1) {
    const data = canvas.toDataURL({ format: "png", multiplier: scale || 1 });
    downloadData("export.png", data);
  }
  function exportThumbnail() {
    const data = canvas.toDataURL({ format: "png", multiplier: 0.2 });
    downloadData("thumb.png", data);
  }
  function exportSVG() {
    const svg = canvas.toSVG();
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    downloadBlob("export.svg", blob);
  }
  function exportJSONFile() {
    const st = serializeLayersFromCanvas();
    const blob = new Blob([JSON.stringify(st, null, 2)], { type: "application/json" });
    downloadBlob("plantilla.json", blob);
  }
  function importJSONFile(file) {
    const r = new FileReader();
    r.onload = () => {
      try {
        const data = JSON.parse(String(r.result || "{}"));
        const page = (data.pages && data.pages[0]) || DEFAULT_STATE.pages[0];
        resizeCanvasToPage(page);
        loadLayersFromJSON(page.layers || []);
        setState(data);
        pushHistory();
      } catch (e) {
        console.error(e);
        setStatus("⚠️ JSON inválido");
      }
    };
    r.readAsText(file);
  }
  function downloadData(filename, href) {
    const a = document.createElement("a");
    a.href = href; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
  }
  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob);
    downloadData(filename, url);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  // ----- importar local -----
  function bindImporter() {
    const btn = $("#btnOpenDoc");
    const inp = $("#openDocFile");
    if (!btn || !inp) return;

    btn.addEventListener("click", () => inp.click());
    inp.addEventListener("change", async () => {
      const f = inp.files?.[0];
      inp.value = "";
      if (!f) return;
      await importLocalFile(f);
    });
  }

  async function importLocalFile(file) {
    try {
      const type = (file.type || "").toLowerCase();
      setStatus("Importando…");

      if (type.startsWith("image/")) {
        await importImageFile(file);
        setStatus("✅ Imagen importada");
        return;
      }
      if (type === "application/pdf" || /\.pdf$/i.test(file.name)) {
        if (!window.pdfjsLib) throw new Error("PDF.js no está cargado");
        await importPDFFile(file);
        setStatus("✅ PDF importado");
        return;
      }
      if (/\.(docx?|pptx?|odt|odp)$/i.test(file.name)) {
        const url = window.IMPORT_CONVERT_URL;
        if (!url) throw new Error("IMPORT_CONVERT_URL no está definido");
        await importOfficeViaBackend(file, url);
        setStatus("✅ Documento importado");
        return;
      }
      setStatus("⚠️ Tipo no soportado");
    } catch (e) {
      console.error(e);
      setStatus("⚠️ Error en importación");
    }
  }

  function importImageFile(file) {
    const r = new FileReader();
    return new Promise((resolve) => {
      r.onload = () => {
        // eslint-disable-next-line no-undef
        fabric.Image.fromURL(String(r.result || ""), (img) => {
          if (!img) return resolve();
          const pageW = canvas.width, pageH = canvas.height;
          const scale = Math.min(pageW / img.width, pageH / img.height, 1);
          img.set({ left: 0, top: 0, scaleX: scale, scaleY: scale });
          canvas.add(img).setActiveObject(img);
          canvas.renderAll();
          setTimeout(pushHistoryDebounced, 0);
          resolve();
        }, { crossOrigin: "anonymous" });
      };
      r.readAsDataURL(file);
    });
  }

  // Limita la resolución de rasterizado para evitar bloqueos del hilo principal
  async function importPDFFile(file) {
    const buf = await file.arrayBuffer();
    const pdf = await window.pdfjsLib.getDocument({ data: buf }).promise;
    const page = await pdf.getPage(1);

    const vpProbe = page.getViewport({ scale: 1 });
    const MAX_SIDE = 1800; // tope de lado (ajustable)
    const maxDim  = Math.max(vpProbe.width, vpProbe.height);
    const scale   = Math.min(2, Math.max(0.5, MAX_SIDE / maxDim));

    const viewport = page.getViewport({ scale });
    const canvasTmp = document.createElement("canvas");
    const ctx = canvasTmp.getContext("2d", { willReadFrequently: true });
    canvasTmp.width  = viewport.width | 0;
    canvasTmp.height = viewport.height | 0;

    await page.render({ canvasContext: ctx, viewport }).promise;

    const dataURL = canvasTmp.toDataURL("image/png");
    return new Promise((resolve) => {
      // eslint-disable-next-line no-undef
      fabric.Image.fromURL(dataURL, (img) => {
        if (!img) return resolve();
        const pageW = canvas.width, pageH = canvas.height;
        const scaleToFit = Math.min(pageW / img.width, pageH / img.height, 1);
        img.set({ left: 0, top: 0, scaleX: scaleToFit, scaleY: scaleToFit });
        canvas.add(img).setActiveObject(img);
        canvas.renderAll();
        setTimeout(pushHistoryDebounced, 0);
        resolve();
      });
    });
  }

  async function importOfficeViaBackend(file, convertUrl) {
    const fd = new FormData();
    fd.append("file", file);

    const resp = await fetch(convertUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCSRFToken() },
      body: fd,
      credentials: "include",
    });

    if (!resp.ok) {
      if (resp.status === 501) {
        setStatus("⚠️ Conversión de Office no habilitada en el servidor.");
        return; // salir sin lanzar excepción
      }
      if (resp.status === 405) {
        setStatus("⚠️ Endpoint de conversión requiere método POST.");
        return;
      }
      setStatus(`⚠️ Error de conversión (${resp.status})`);
      return;
    }

    const data = await resp.json();

    // Si el backend devuelve imágenes ya rasterizadas
    if (data.images && data.images.length) {
      await new Promise((resolve) => {
        // eslint-disable-next-line no-undef
        fabric.Image.fromURL(data.images[0], (img) => {
          if (!img) return resolve();
          const pageW = canvas.width, pageH = canvas.height;
          const scale = Math.min(pageW / img.width, pageH / img.height);
          img.set({ left: 0, top: 0, scaleX: scale, scaleY: scale });
          canvas.add(img).setActiveObject(img);
          canvas.renderAll();
          setTimeout(pushHistoryDebounced, 0);
          resolve();
        }, { crossOrigin: "anonymous" });
      });
      return;
    }

    // O si devuelve un PDF, lo tratamos con el pipeline de PDF (cliente)
    if (data.pdf_url) {
      const r = await fetch(data.pdf_url, { credentials: "include" });
      const blob = await r.blob();
      await importPDFFile(new File([blob], "converted.pdf", { type: "application/pdf" }));
      return;
    }

    setStatus("⚠️ Respuesta de conversión no reconocida");
  }

  // ----- status -----
  let _statusT;
  function setStatus(msg) {
    const el = $("#status");
    if (!el) return;
    el.textContent = msg || "";
    clearTimeout(_statusT);
    if (msg && /✅|⚠️|Listo|Guardado/.test(msg)) {
      _statusT = setTimeout(() => { el.textContent = ""; }, 2500);
    }
  }

})();
