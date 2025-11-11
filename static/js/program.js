/* program.js – lista de programas (buscador, borrar, paginación, alertas) */
(function () {
  "use strict";

  // ==========================
  // Helpers básicos
  // ==========================
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  // Pequeño debounce para no spamear el servidor con el buscador
  function debounce(fn, delay) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  // ==========================
  // 1) Buscador con auto-submit
  // ==========================
  function initSearch() {
    const searchInput = $("#q") || $("input[name='q']");
    if (!searchInput) return;

    const form = searchInput.closest("form");
    if (!form) return;

    const submitDebounced = debounce(() => {
      form.requestSubmit();
    }, 400);

    searchInput.addEventListener("input", submitDebounced);
  }

  // =====================================
  // 2) Modal de confirmación para BORRAR
  // =====================================
  function initDeleteModal() {
    const modal  = $("#confirmModal");
    if (!modal) return;

    const nameEl = $("#confirmName", modal);
    const codeEl = $("#confirmCode", modal);
    const btnYes = $("#confirmYes", modal);
    const btnNo  = $("#confirmNo", modal);

    let currentFormId = null;

    function openModal(formId, programName, code) {
      currentFormId = formId || null;
      if (nameEl) nameEl.textContent = programName || "";
      if (codeEl) codeEl.textContent = code || "";

      modal.classList.remove("is-hidden");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");

      if (btnYes) btnYes.focus();
    }

    function closeModal() {
      // Quitar foco antes de ocultar para evitar warnings de accesibilidad
      const active = document.activeElement;
      if (active && modal.contains(active) && typeof active.blur === "function") {
        active.blur();
      }

      modal.classList.add("is-hidden");
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("modal-open");
      currentFormId = null;
    }

    // Cerrar con overlay o cualquier elemento con data-modal-close
    modal.addEventListener("click", (ev) => {
      const target = ev.target;
      if (!target) return;
      if (target.hasAttribute("data-modal-close")) {
        closeModal();
      }
    });

    if (btnNo) {
      btnNo.addEventListener("click", closeModal);
    }

    if (btnYes) {
      btnYes.addEventListener("click", () => {
        if (!currentFormId) {
          closeModal();
          return;
        }
        const form = document.getElementById(currentFormId);
        if (form) form.submit();
        closeModal();
      });
    }

    // Delegar clic en los botones .js-del (los de la tabla)
    document.addEventListener("click", (ev) => {
      const btn = ev.target.closest && ev.target.closest(".js-del");
      if (!btn) return;

      // Si el botón está deshabilitado por alguna razón, no abrimos modal
      if (btn.disabled) return;

      const formId      = btn.getAttribute("data-form-id");
      const programName = btn.getAttribute("data-program") || "";
      const code        = btn.getAttribute("data-code") || "";

      if (!formId) {
        console.warn("[program.js] Botón .js-del sin data-form-id");
        return;
      }
      openModal(formId, programName, code);
    });

    // Cerrar con la tecla ESC
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && modal.getAttribute("aria-hidden") === "false") {
        closeModal();
      }
    });
  }

  // ==============================
  // 3) Paginación de la tabla
  // ==============================
  function initPager() {
    const tbody   = $(".table__body");
    const pager   = $("#programPager");
    const section = $(".card.card--secondary"); // Sección de Programas

    if (!tbody || !pager) return;

    const allRows  = Array.from(tbody.querySelectorAll("tr"));
    const emptyRow = allRows.find(r => r.querySelector(".table__cell--empty"));
    const dataRows = emptyRow ? allRows.filter(r => r !== emptyRow) : allRows;

    const pageSize = 10;

    // Si hay pocos registros, escondemos el paginador
    if (dataRows.length <= pageSize) {
      pager.style.display = "none";
      if (emptyRow) {
        emptyRow.style.display = dataRows.length ? "none" : "";
      }
      return;
    }

    pager.style.display = "flex";

    const totalPages = Math.ceil(dataRows.length / pageSize);
    let currentPage  = 0;

    function renderPage(page, options) {
      const opts     = options || {};
      const doScroll = opts.scroll !== false;

      if (page < 0) page = 0;
      if (page >= totalPages) page = totalPages - 1;
      currentPage = page;

      const start = currentPage * pageSize;
      const end   = start + pageSize;

      dataRows.forEach((row, idx) => {
        row.style.display = (idx >= start && idx < end) ? "" : "none";
      });

      if (emptyRow) {
        emptyRow.style.display = "none";
      }

      // Dibujar los "puntitos" del paginador
      pager.innerHTML = "";
      for (let i = 0; i < totalPages; i++) {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "pager__dot" + (i === currentPage ? " is-active" : "");
        dot.setAttribute("aria-label", "Ir a página " + (i + 1));
        dot.addEventListener("click", () => renderPage(i, { scroll: true }));
        pager.appendChild(dot);
      }

      // Scroll suave hacia la sección de Programas
      if (doScroll && section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }

    // Primera página, sin hacer scroll
    renderPage(0, { scroll: false });
  }

  // =========================================
  // 4) Alertas con auto-cierre y progreso
  // =========================================
  function initAlerts() {
    const AUTO_CLOSE_MS = 10000; // 10 segundos

    function setupAlert(alert) {
      const progressBar = alert.querySelector(".alert__progress-bar");
      const closeBtn    = alert.querySelector(".alert__close");
      let closed = false;
      const start = Date.now();

      function closeAlert() {
        if (closed) return;
        closed = true;
        alert.classList.add("alert--closing");
        window.setTimeout(() => {
          if (alert && alert.parentElement) {
            alert.parentElement.removeChild(alert);
          }
        }, 350);
      }

      if (closeBtn) {
        closeBtn.addEventListener("click", closeAlert);
      }

      function tick() {
        if (closed) return;
        const elapsed = Date.now() - start;
        const ratio   = Math.min(1, elapsed / AUTO_CLOSE_MS);

        if (progressBar) {
          progressBar.style.width = (100 - ratio * 100) + "%";
        }

        if (elapsed >= AUTO_CLOSE_MS) {
          closeAlert();
        } else {
          window.requestAnimationFrame(tick);
        }
      }

      if (progressBar) {
        progressBar.style.width = "100%";
        window.requestAnimationFrame(tick);
      }
    }

    const alerts = $$(".alert-stack .alert");
    if (!alerts.length) return;
    alerts.forEach(setupAlert);
  }

  // =========================================
  // 5) Reset de modales al cargar la página
  // =========================================
  function resetModalsOnLoad() {
    document.body.classList.remove("modal-open");
    const modals = $$(".confirm-modal");
    modals.forEach((modal) => {
      modal.classList.add("is-hidden");
      modal.setAttribute("aria-hidden", "true");
    });
  }

  // =========================================
  // Bootstrap
  // =========================================
  onReady(() => {
    resetModalsOnLoad();
    initSearch();
    initDeleteModal();
    initPager();
    initAlerts();
  });
})();
