/* program.js — lista + formulario (CSP-friendly, sin inline) */
(function () {
  "use strict";

  // ---------- Helpers ----------
  const $  = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const on = (el, ev, fn, opts) => el && el.addEventListener(ev, fn, opts);
  const debounce = (fn, ms=300) => { let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; };

  // =========================================================
  // ===============  PÁGINA: LISTA DE PROGRAMAS  ============
  // =========================================================
  (function bootList(){
    const searchInput = $("#q") || $('input[name="q"]');
    const listForm    = searchInput ? searchInput.closest("form") : null;

    // Auto-submit al escribir con debounce
    if (searchInput && listForm) {
      on(searchInput, "input", debounce(() => listForm.requestSubmit(), 400));
    }

    // Confirmación para eliminar (marca los forms con class o data-attr)
    // Ejemplo HTML:
    // <form class="js-delete-form" data-delete="program" data-program-name="{{ p.name }}">...</form>
    const deleteForms = $$('form.js-delete-form,[data-delete="program"]');
    deleteForms.forEach(form => {
      on(form, "submit", (e) => {
        const name = form.dataset.programName || form.getAttribute("data-name") || "este programa";
        if (!confirm(`¿Eliminar ${name}? Esta acción no se puede deshacer.`)) {
          e.preventDefault();
        }
      });
    });
  })();

  // =========================================================
  // ===============  PÁGINA: FORM DE PLANTILLA  =============
  // =========================================================
  (function bootForm(){
    const editor   = $("#json");
    const badge    = $("#validBadge");
    const sizeInfo = $("#sizeInfo");
    const canvas   = $("#preview");
    const pretty   = $("#btnPretty");
    const validate = $("#btnValidate");
    const form     = $("#tplForm");

    if (!editor || !canvas) return; // no estamos en el form
    const ctx = canvas.getContext("2d");

    // ---- Layout por defecto y presets ----
    function defaultLayout(){
      return { pages: [ { width: 1920, height:1080, background:"#ffffff", layers: [] } ] };
    }
    const presets = {
      fhd:     { pages: [{ width:1920, height:1080, background:"#ffffff", layers: [] }] },
      a4:      { pages: [{ width:2480, height:3508, background:"#ffffff", layers: [] }] }, // 300dpi
      letter:  { pages: [{ width:2550, height:3300, background:"#ffffff", layers: [] }] }, // 300dpi
      square:  { pages: [{ width:1080, height:1080, background:"#ffffff", layers: [] }] },
      blank:   { pages: [{ width:800,  height:600,  background:"#ffffff", layers: [] }] },
    };

    // ---- Dibujo de preview (fondo oscuro, hoja, borde y cuadrícula) ----
    function drawPreview(w=800, h=600, bg="#ffffff"){
      const maxW = canvas.width, maxH = canvas.height;
      const scale = Math.min(maxW / w, maxH / h);
      const vw = Math.max(60, w * scale);
      const vh = Math.max(60, h * scale);
      const ox = (maxW - vw) / 2, oy = (maxH - vh) / 2;

      // Fondo del canvas (match con tu UI oscura)
      ctx.fillStyle = "#0b0d10";
      ctx.fillRect(0, 0, maxW, maxH);

      // Área del documento
      ctx.fillStyle = bg || "#ffffff";
      ctx.fillRect(ox, oy, vw, vh);

      // Borde de la hoja
      ctx.strokeStyle = "#374151";
      ctx.lineWidth = 2;
      ctx.strokeRect(ox, oy, vw, vh);

      // Cuadrícula
      ctx.lineWidth = 1;
      ctx.strokeStyle = "#1f2937";
      const grid = 50 * scale;
      if (grid >= 6) {
        for (let x = ox + grid; x < ox + vw; x += grid){ ctx.beginPath(); ctx.moveTo(x, oy); ctx.lineTo(x, oy + vh); ctx.stroke(); }
        for (let y = oy + grid; y < oy + vh; y += grid){ ctx.beginPath(); ctx.moveTo(ox, y); ctx.lineTo(ox + vw, y); ctx.stroke(); }
      }

      if (sizeInfo) sizeInfo.textContent = `${Math.round(w)} × ${Math.round(h)} px`;
    }

    // ---- Badge de estado ----
    function setBadge(ok, msgOk="Válido", msgBad="JSON inválido"){
      if (!badge) return;
      badge.classList.remove("ok","bad");
      badge.classList.add(ok ? "ok":"bad");
      badge.textContent = ok ? msgOk : msgBad;
    }

    // ---- Parse / validar JSON ----
    function parseEditor(){
      const txt = (editor.value || "").trim();
      if (!txt) return { ok:true, data: defaultLayout(), empty:true };
      try {
        const data = JSON.parse(txt);
        if (!data.pages || !data.pages.length) {
          return { ok:false, error:"Debe existir pages[0] con width, height y background." };
        }
        const p = data.pages[0];
        if (typeof p.width !== "number" || typeof p.height !== "number"){
          return { ok:false, error:"width y height deben ser números." };
        }
        if (typeof p.background !== "string"){
          return { ok:false, error:"background debe ser string (ej. “#ffffff”)." };
        }
        return { ok:true, data, empty:false };
      } catch(e){
        return { ok:false, error:e.message };
      }
    }

    // ---- Validar + preview ----
    function validateAndPreview(){
      const res = parseEditor();
      if (!res.ok){
        setBadge(false, "", "JSON inválido");
        drawPreview(800, 600, "#111827");
        if (sizeInfo) sizeInfo.textContent = "—";
        return false;
      }
      setBadge(true, res.empty ? "Se usará por defecto" : "Válido");
      const p = res.data.pages[0];
      drawPreview(p.width, p.height, p.background);
      return true;
    }

    // ---- Eventos ----
    on(editor, "input", debounce(validateAndPreview, 150));

    on(pretty, "click", () => {
      const res = parseEditor();
      if (res.ok) {
        editor.value = JSON.stringify(res.data, null, 2);
        validateAndPreview();
      }
    });
    on(validate, "click", validateAndPreview);

    $$(".pill[data-preset]").forEach(el => {
      on(el, "click", ()=>{
        const key = el.dataset.preset;
        const preset = presets[key] || defaultLayout();
        editor.value = JSON.stringify(preset, null, 2);
        validateAndPreview();
      });
    });

    on(form, "submit", (e)=>{
      const res = parseEditor();
      if (!res.ok){
        e.preventDefault();
        alert("Corrige el JSON: " + (res.error || "inválido"));
        return;
      }
      if (res.empty){
        editor.value = JSON.stringify(defaultLayout());
      }
    });

    // Primer render
    validateAndPreview();
  })();
})();
(function () {
  // ------ Helpers ------
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  // ------ Canvas preview (compartido para program_form y plantillas_form) ------
  const canvas = $("#preview");
  const ctx = canvas ? canvas.getContext("2d") : null;
  const sizeInfo = $("#sizeInfo");
  const badge = $("#validBadge");

  const presets = {
    fhd:     { pages: [{ width: 1920, height:1080, background:"#ffffff", layers: [] }] },
    a4:      { pages: [{ width: 2480, height:3508, background:"#ffffff", layers: [] }] },
    letter:  { pages: [{ width: 2550, height:3300, background:"#ffffff", layers: [] }] },
    legal:   { pages: [{ width: 2550, height:4200, background:"#ffffff", layers: [] }] },
    square:  { pages: [{ width: 1080, height:1080, background:"#ffffff", layers: [] }] },
    blank:   { pages: [{ width: 800,  height:600,  background:"#ffffff", layers: [] }] },
  };

  function defaultLayout() {
    return presets.fhd;
  }

  function drawPreview(w=800, h=600, bg="#ffffff") {
    if (!ctx) return;
    const maxW = canvas.width, maxH = canvas.height;
    const scale = Math.min(maxW / w, maxH / h);
    const vw = Math.max(60, w * scale);
    const vh = Math.max(60, h * scale);
    const ox = (maxW - vw) / 2, oy = (maxH - vh) / 2;

    // Fondo canvas
    ctx.fillStyle = "#0b0d10";
    ctx.fillRect(0, 0, maxW, maxH);

    // Área del lienzo
    ctx.fillStyle = bg || "#ffffff";
    ctx.fillRect(ox, oy, vw, vh);

    // Borde
    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 2;
    ctx.strokeRect(ox, oy, vw, vh);

    // Cuadrícula
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#1f2937";
    const grid = 50 * scale;
    if (grid >= 6) {
      for (let x = ox + grid; x < ox + vw; x += grid) {
        ctx.beginPath(); ctx.moveTo(x, oy); ctx.lineTo(x, oy + vh); ctx.stroke();
      }
      for (let y = oy + grid; y < oy + vh; y += grid) {
        ctx.beginPath(); ctx.moveTo(ox, y); ctx.lineTo(ox + vw, y); ctx.stroke();
      }
    }
    if (sizeInfo) sizeInfo.textContent = `${Math.round(w)} × ${Math.round(h)} px`;
  }

  function setBadge(ok, msgOk="Válido", msgBad="JSON inválido") {
    if (!badge) return;
    badge.classList.remove("ok","bad");
    badge.classList.add(ok ? "ok" : "bad");
    badge.textContent = ok ? msgOk : msgBad;
  }

  function parseJSONArea(textarea) {
    const txt = (textarea.value || "").trim();
    if (!txt) return { ok:true, data: defaultLayout(), empty:true };
    try {
      const data = JSON.parse(txt);
      if (!data.pages || !data.pages.length) {
        return { ok:false, error:"Falta pages[0]." };
      }
      const p = data.pages[0];
      if (typeof p.width !== "number" || typeof p.height !== "number") {
        return { ok:false, error:"width/height deben ser numéricos." };
      }
      if (typeof p.background !== "string") {
        return { ok:false, error:"background debe ser string (#rrggbb)." };
      }
      return { ok:true, data, empty:false };
    } catch (e) {
      return { ok:false, error:e.message };
    }
  }

  function bindEditor(jsonSelector) {
    const editor = $(jsonSelector);
    if (!editor) return;

    function validateAndPreview() {
      const res = parseJSONArea(editor);
      if (!res.ok) {
        setBadge(false);
        drawPreview(800, 600, "#111827");
        return false;
      }
      setBadge(true, res.empty ? "Se usará por defecto" : "Válido");
      const p = res.data.pages[0];
      drawPreview(p.width, p.height, p.background);
      return true;
    }

    editor.addEventListener("input", validateAndPreview);
    const pretty = $("#btnPretty"); if (pretty) pretty.addEventListener("click", () => {
      const res = parseJSONArea(editor);
      if (res.ok) editor.value = JSON.stringify(res.data, null, 2), validateAndPreview();
    });
    const validate = $("#btnValidate"); if (validate) validate.addEventListener("click", validateAndPreview);

    $$(".pill[data-size]").forEach(btn => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.size;
        const preset = presets[key] || defaultLayout();
        editor.value = JSON.stringify(preset, null, 2);
        validateAndPreview();
      });
    });

    // Primera carga
    validateAndPreview();

    // Al submit, asegura layout válido/por defecto
    const form = editor.closest("form");
    if (form) {
      form.addEventListener("submit", (e) => {
        const res = parseJSONArea(editor);
        if (!res.ok) {
          e.preventDefault();
          alert("Corrige el JSON: " + (res.error || "inválido"));
          return;
        }
        if (res.empty) {
          editor.value = JSON.stringify(defaultLayout());
        }
      });
    }
  }

  // Plantillas form
  if ($("#tplForm")) bindEditor("#json");
  // Program form
  if ($("#programForm")) bindEditor("#layout_json");
})();
(function () {
  function ready(fn) {
    if (document.readyState !== "loading") { fn(); }
    else { document.addEventListener("DOMContentLoaded", fn); }
  }

  function getCsrfFromFirstDeleteForm() {
    const inp = document.querySelector(".js-delete-form input[name='csrfmiddlewaretoken']");
    return inp ? inp.value : null;
    // Nota: CSRF cookie es HttpOnly por configuración; tomamos el token del input del form.
  }

  ready(function () {
    // --- Confirmación de eliminación por fila ---
    document.querySelectorAll(".js-delete-form").forEach(function (form) {
      const btn = form.querySelector(".js-delete-btn");
      if (!btn) return;
      btn.addEventListener("click", function (ev) {
        const name = btn.getAttribute("data-name") || "este programa";
        const ok = window.confirm(`¿Seguro que deseas eliminar ${name}? Esta acción no se puede deshacer.`);
        if (!ok) ev.preventDefault();
      });
    });

    // --- Selección múltiple ---
    const checkAll = document.getElementById("checkAll");
    const rowChecks = Array.from(document.querySelectorAll(".row-check"));
    const selCount = document.getElementById("selCount");
    const bulkBtn  = document.getElementById("bulkDeleteBtn");

    function updateState() {
      const n = rowChecks.filter(c => c.checked).length;
      selCount && (selCount.textContent = `${n} seleccionados`);
      if (bulkBtn) bulkBtn.disabled = n === 0;
      if (checkAll) {
        const all = rowChecks.length > 0 && n === rowChecks.length;
        const some = n > 0 && n < rowChecks.length;
        checkAll.checked = all;
        checkAll.indeterminate = some;
      }
    }
    updateState();

    if (checkAll) {
      checkAll.addEventListener("change", function () {
        rowChecks.forEach(c => { c.checked = checkAll.checked; });
        updateState();
      });
    }
    rowChecks.forEach(c => c.addEventListener("change", updateState));

    // --- Eliminación masiva usando fetch a cada endpoint existente ---
    if (bulkBtn) {
      bulkBtn.addEventListener("click", async function () {
        const selectedRows = rowChecks.filter(c => c.checked).map(c => c.closest("tr"));
        if (!selectedRows.length) return;

        const names = selectedRows.map(tr => {
          const btn = tr.querySelector(".js-delete-btn");
          return btn ? (btn.getAttribute("data-name") || "programa") : "programa";
        });

        const ok = window.confirm(
          `¿Eliminar ${selectedRows.length} elemento(s)?\n\n` +
          names.slice(0, 8).join("\n") + (names.length > 8 ? `\n…` : ``) +
          `\n\nEsta acción no se puede deshacer.`
        );
        if (!ok) return;

        const csrf = getCsrfFromFirstDeleteForm();
        if (!csrf) {
          alert("No se encontró token CSRF. Recarga la página e inténtalo de nuevo.");
          return;
        }

        // Ejecutamos en serie para evitar saturar y para respetar vistas que redirigen.
        for (const tr of selectedRows) {
          const endpointEl = tr.querySelector(".js-delete-endpoint");
          const url = endpointEl ? endpointEl.getAttribute("data-url") : null;
          if (!url) continue;
          try {
            const resp = await fetch(url, {
              method: "POST",
              headers: {
                "X-CSRFToken": csrf
              },
              redirect: "follow"
            });
            // Opcional: podríamos validar resp.ok; como las vistas suelen redirigir, lo dejamos laxo.
          } catch (e) {
            console.error("Error al eliminar:", e);
          }
        }
        // Al terminar, recargamos para ver el estado actualizado.
        window.location.reload();
      });
    }
  });
})();
(function () {
  function ready(fn) {
    if (document.readyState !== "loading") { fn(); }
    else { document.addEventListener("DOMContentLoaded", fn); }
  }

  function getCsrfFromFirstDeleteForm() {
    const inp = document.querySelector(".js-delete-form input[name='csrfmiddlewaretoken']");
    return inp ? inp.value : null;
  }

  function getAllIdsFromBox() {
    const box = document.getElementById("allIdsBox");
    if (!box) return [];
    const raw = box.getAttribute("data-all-ids") || "";
    return raw.split(",").map(s => s.trim()).filter(Boolean);
  }

  function uniq(arr) {
    return Array.from(new Set(arr));
  }

  ready(function () {
    // Confirmación por fila
    document.querySelectorAll(".js-delete-form").forEach(function (form) {
      const btn = form.querySelector(".js-delete-btn");
      if (!btn) return;
      btn.addEventListener("click", function (ev) {
        const name = btn.getAttribute("data-name") || "este programa";
        const ok = window.confirm(`¿Seguro que deseas eliminar “${name}”? Esta acción no se puede deshacer.`);
        if (!ok) ev.preventDefault();
      });
    });

    // Selección en tabla (modo "página")
    const checkAll = document.getElementById("checkAll");
    const rowChecks = Array.from(document.querySelectorAll(".row-check"));
    const selCount = document.getElementById("selCount");
    const bulkBtn  = document.getElementById("bulkDeleteBtn");

    // Modo de selección
    let mode = "page"; // "page" | "all"
    const modePageBtn = document.getElementById("modePageBtn");
    const modeAllBtn  = document.getElementById("modeAllBtn");

    function setMode(newMode) {
      mode = newMode;
      if (modePageBtn && modeAllBtn) {
        modePageBtn.classList.toggle("is-active", mode === "page");
        modeAllBtn.classList.toggle("is-active", mode === "all");
      }
      updateState();
    }

    if (modePageBtn) modePageBtn.addEventListener("click", () => setMode("page"));
    if (modeAllBtn)  modeAllBtn.addEventListener("click", () => setMode("all"));

    function selectedIdsPage() {
      return rowChecks.filter(c => c.checked).map(c => c.value);
    }

    function endpointsForIds(ids) {
      // Busca cada <tr data-id="..."> y lee su span .js-delete-endpoint
      const urls = [];
      ids.forEach(id => {
        const tr = document.querySelector(`tr[data-id="${CSS.escape(id)}"]`);
        if (!tr) return; // Si no está en el DOM (paginación), no tenemos su endpoint
        const el = tr.querySelector(".js-delete-endpoint");
        const url = el ? el.getAttribute("data-url") : null;
        if (url) urls.push({ id, url });
      });
      return urls;
    }

    function updateState() {
      let n = 0;
      if (mode === "page") {
        n = selectedIdsPage().length;
      } else {
        const allIds = getAllIdsFromBox();
        n = allIds.length;
      }
      if (selCount) selCount.textContent = `${n} seleccionados (${mode === "page" ? "página" : "todos"})`;
      if (bulkBtn) bulkBtn.disabled = n === 0;
      if (checkAll && mode === "page") {
        const total = rowChecks.length;
        const pageSelected = selectedIdsPage().length;
        checkAll.checked = total > 0 && pageSelected === total;
        checkAll.indeterminate = pageSelected > 0 && pageSelected < total;
      }
      if (checkAll && mode === "all") {
        // En modo "todos", el checkbox maestro no aplica a todo el dataset.
        checkAll.checked = false;
        checkAll.indeterminate = false;
      }
    }
    updateState();

    if (checkAll) {
      checkAll.addEventListener("change", function () {
        if (mode !== "page") return; // solo página
        rowChecks.forEach(c => { c.checked = checkAll.checked; });
        updateState();
      });
    }
    rowChecks.forEach(c => c.addEventListener("change", updateState));

    // Eliminación masiva
    if (bulkBtn) {
      bulkBtn.addEventListener("click", async function () {
        const csrf = getCsrfFromFirstDeleteForm();
        if (!csrf) {
          alert("No se encontró token CSRF. Recarga la página e inténtalo de nuevo.");
          return;
        }

        let ids = [];
        if (mode === "page") {
          ids = selectedIdsPage();
        } else {
          ids = getAllIdsFromBox();
          if (!ids.length) {
            alert("No recibimos el listado completo de IDs. Vuelve a cargar la página o usa ‘Esta página’.");
            return;
          }
        }
        ids = uniq(ids);

        // Confirmación
        const total = ids.length;
        const ok = window.confirm(
          `¿Eliminar ${total} elemento(s) en modo “${mode === "page" ? "Esta página" : "Todos los resultados"}”?` +
          `\n\nEsta acción no se puede deshacer.`
        );
        if (!ok) return;

        // Resolvemos endpoints para los IDs visibles.
        // Nota: Para IDs no visibles (porque están en otras páginas), no tenemos su URL de fila.
        // Si quieres eliminación real de “todos” sin depender del DOM,
        // define un endpoint de bulk en el servidor (te dejé el snippet más abajo).
        const pairs = endpointsForIds(ids);

        // Si faltan URLs y estamos en "all", avisamos.
        if (mode === "all" && pairs.length < ids.length) {
          const diff = ids.length - pairs.length;
          const cont = window.confirm(
            `Solo puedo eliminar ${pairs.length} de ${ids.length} seleccionados desde el cliente (restan ${diff} en otras páginas).` +
            `\n\n¿Deseas continuar con los visibles?`
          );
          if (!cont) return;
        }

        for (const { url } of pairs) {
          try {
            await fetch(url, { method: "POST", headers: { "X-CSRFToken": csrf }, redirect: "follow" });
          } catch (e) {
            console.error("Error al eliminar:", e);
          }
        }
        window.location.reload();
      });
    }
  });
})();
