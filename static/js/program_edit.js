// program_edit.js — Modal + AJAX para editar programas
(function () {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  // Busca el token CSRF en cualquier <input name="csrfmiddlewaretoken">
  function getCsrfToken() {
    const input = document.querySelector("input[name='csrfmiddlewaretoken']");
    return input ? input.value : null;
  }

  // ---------- Alertas reutilizables ----------
  function createAlertStack() {
    let stack = $(".alert-stack");
    if (!stack) {
      stack = document.createElement("section");
      stack.className = "alert-stack";
      const header = $(".page__header") || document.body.firstElementChild;
      if (header && header.parentElement) {
        header.parentElement.insertBefore(stack, header.nextSibling);
      } else {
        document.body.prepend(stack);
      }
    }
    return stack;
  }

  function setupAlertAutoClose(alert) {
    const AUTO_CLOSE_MS = 10000;
    const progressBar = alert.querySelector(".alert__progress-bar");
    const closeBtn = alert.querySelector(".alert__close");
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
      const ratio = Math.min(1, elapsed / AUTO_CLOSE_MS);

      if (progressBar) {
        progressBar.style.width = `${100 - ratio * 100}%`;
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

  function showAlert(type, text) {
    const stack = createAlertStack();
    const alert = document.createElement("div");
    alert.className = `alert alert--${type || "info"}`;
    alert.innerHTML = `
      <button
        type="button"
        class="alert__close"
        aria-label="Cerrar notificación"
      >×</button>
      <span class="alert__text">${text}</span>
      <div class="alert__progress">
        <div class="alert__progress-bar"></div>
      </div>
    `;
    stack.appendChild(alert);
    setupAlertAutoClose(alert);
  }

  // ---------- Modal editar programa ----------
  function initProgramEditModal() {
    const modal   = $("#programEditModal");
    const form    = $("#programEditForm");
    const saveBtn = $("#programEditSave");
    if (!modal || !form || !saveBtn) return;

    const inputId   = $("#editId");
    const inputCode = $("#editCode");
    const inputName = $("#editName");

    // >>> NUEVO: referencias a campo de DIPLOMA
    const fieldDiploma    = $("#fieldTplDiploma");
    const selectDiploma   = $("#editTplDiploma");
    const helpDiploma     = $("#editTplDiplomaCurrent");
    // <<< NUEVO

    const fieldDc3        = $("#fieldTplDc3");
    const fieldCproem     = $("#fieldTplCproem");
    const selectDc3Front  = $("#editTplDc3Front");
    const selectDc3Back   = $("#editTplDc3Back");
    const selectCproem    = $("#editTplCproem");
    const helpDc3         = $("#editTplDc3Current");
    const helpCproem      = $("#editTplCproemCurrent");

    let activeButton = null;
    let activeRow    = null;

    function updateTemplateVisibility(constancia) {
      const c = (constancia || "").toLowerCase();
      if (fieldDc3)    fieldDc3.style.display    = c === "dc3"    ? "" : "none";
      if (fieldCproem) fieldCproem.style.display = c === "cproem" ? "" : "none";
      // El diploma siempre se puede editar, así que no lo escondemos.
    }

    function setSelectValue(selectEl, value) {
      if (!selectEl) return;
      if (!value) {
        selectEl.value = "";
        return;
      }
      const opt = selectEl.querySelector(`option[value="${value}"]`);
      selectEl.value = opt ? value : "";
    }

    function optionLabel(selectEl, value) {
      if (!selectEl || !value) return null;
      const opt = selectEl.querySelector(`option[value="${value}"]`);
      return opt ? opt.textContent.trim() : null;
    }

    function openModalForButton(btn) {
      activeButton = btn;
      const tr = btn.closest("tr");
      activeRow = tr || null;

      const id         = btn.dataset.id;
      const code       = btn.dataset.code || "";
      const name       = btn.dataset.name || "";
      const constancia = (btn.dataset.constancia || "").toLowerCase();

      // IDs de plantillas actuales
      const dc3FrontId    = btn.dataset.dc3Front    || "";
      const dc3BackId     = btn.dataset.dc3Back     || "";
      const cproemTplId   = btn.dataset.cproemTpl   || "";
      const diplomaTplId  = btn.dataset.diplomaTpl  || "";  // >>> NUEVO

      if (inputId)   inputId.value   = id || "";
      if (inputCode) inputCode.value = code;
      if (inputName) inputName.value = name;

      // Radios constancia
      const radios = $$("input[name='editConstancia']", form);
      radios.forEach(r => { r.checked = r.value === constancia; });
      if (!radios.some(r => r.checked)) {
        const dc3 = radios.find(r => r.value === "dc3");
        if (dc3) dc3.checked = true;
      }

      const finalConst = (radios.find(r => r.checked)?.value || constancia || "dc3").toLowerCase();
      updateTemplateVisibility(finalConst);

      // Preseleccionar selects con los valores actuales
      setSelectValue(selectDc3Front, dc3FrontId);
      setSelectValue(selectDc3Back,  dc3BackId);
      setSelectValue(selectCproem,   cproemTplId);
      setSelectValue(selectDiploma,  diplomaTplId);  // >>> NUEVO

      // Texto informativo de plantillas actuales
      // --- DIPLOMA (siempre visible) ---
      if (helpDiploma) {  // >>> NUEVO
        const lblDip = optionLabel(selectDiploma, diplomaTplId);
        helpDiploma.textContent = lblDip
          ? `Plantilla actual de diploma: ${lblDip}`
          : "Este programa aún no tiene plantilla de diploma asociada.";
      }

      if (finalConst === "dc3") {
        const lblF = optionLabel(selectDc3Front, dc3FrontId);
        const lblR = optionLabel(selectDc3Back,  dc3BackId);

        if (helpDc3) {
          if (!lblF && !lblR) {
            helpDc3.textContent = "Este programa aún no tiene plantillas DC3 asociadas.";
          } else {
            const parts = [];
            parts.push(`frontal: ${lblF || "sin frontal asociado"}`);
            parts.push(`reverso: ${lblR || "sin reverso asociado"}`);
            helpDc3.textContent = `Plantillas actuales · ${parts.join(" · ")}`;
          }
        }
        if (helpCproem) helpCproem.textContent = "";
      } else if (finalConst === "cproem") {
        const lbl = optionLabel(selectCproem, cproemTplId);
        if (helpCproem) {
          helpCproem.textContent = lbl
            ? `Plantilla actual: ${lbl}`
            : "Este programa aún no tiene plantilla CPROEM asociada.";
        }
        if (helpDc3) helpDc3.textContent = "";
      }

      modal.classList.add("is-open");
      modal.classList.remove("is-hidden");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");

      if (inputCode) inputCode.focus();
    }

    function closeModal() {
      const active = document.activeElement;
      if (active && modal.contains(active) && typeof active.blur === "function") {
        active.blur();
      }

      modal.classList.remove("is-open");
      modal.classList.add("is-hidden");
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("modal-open");
      activeButton = null;
      activeRow = null;
    }

    // Abrir modal al hacer clic en "Editar"
    $$(".js-program-edit").forEach(btn => {
      btn.addEventListener("click", () => openModalForButton(btn));
    });

    // Cerrar modal con overlay / botones con data-modal-close
    $$("[data-modal-close]", modal).forEach(el => {
      el.addEventListener("click", closeModal);
    });

    // Si cambian el radio de constancia dentro del modal, cambiar los bloques visibles
    $$("input[name='editConstancia']", form).forEach(radio => {
      radio.addEventListener("change", () => {
        updateTemplateVisibility(radio.value);
      });
    });

    // Guardar cambios (AJAX)
    saveBtn.addEventListener("click", async () => {
      if (!activeButton) return;

      const url = activeButton.dataset.url;
      if (!url) {
        showAlert("error", "No se encontró la URL de edición para este programa.");
        return;
      }

      const code  = inputCode.value.trim();
      const name  = inputName.value.trim();
      const radio = $("input[name='editConstancia']:checked", form);
      const constancia = radio ? radio.value : "";

      if (!code || !name) {
        showAlert("error", "«Programa» y «Nombre completo» son obligatorios.");
        return;
      }

      // IDs de plantillas seleccionadas
      const tplDc3FrontId   = selectDc3Front  ? (selectDc3Front.value  || "") : "";
      const tplDc3BackId    = selectDc3Back   ? (selectDc3Back.value   || "") : "";
      const tplCproemId     = selectCproem    ? (selectCproem.value    || "") : "";
      const tplDiplomaId    = selectDiploma   ? (selectDiploma.value   || "") : "";  // >>> NUEVO

      const payload = {
        programa:         code,
        programa_full:    name,
        constancia:       constancia,
        sim_id:           inputId ? inputId.value : null,
        tpl_dc3_front_id: tplDc3FrontId,
        tpl_dc3_back_id:  tplDc3BackId,
        tpl_cproem_id:    tplCproemId,
        tpl_diploma_id:   tplDiplomaId          // >>> NUEVO
      };

      const csrftoken = getCsrfToken();

      try {
        const resp = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken || "",
            "X-Requested-With": "XMLHttpRequest"
          },
          body: JSON.stringify(payload),
        });

        const contentType = resp.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
          showAlert(
            "error",
            "La respuesta del servidor no es válida (¿sesión expirada o error de CSRF?)."
          );
          return;
        }

        const data = await resp.json();

        if (!resp.ok || !data.success) {
          const msg = data && data.message
            ? data.message
            : "No se pudo guardar el programa.";
          showAlert("error", msg);
          return;
        }

        // Actualizar la fila en la tabla, si la tenemos
        if (activeRow) {
          const colCode  = activeRow.querySelector(".js-col-code");
          const colName  = activeRow.querySelector(".js-col-name");
          const colConst = activeRow.querySelector(".js-col-constancia");

          if (colCode)  colCode.textContent  = data.data.programa;
          if (colName)  colName.textContent  = data.data.programa_full;
          if (colConst) colConst.textContent = data.data.constancia;

          activeButton.dataset.code       = data.data.programa;
          activeButton.dataset.name       = data.data.programa_full;
          activeButton.dataset.constancia = data.data.constancia;

          // Actualizar datasets de plantillas (si tu vista los devuelve)
          if (data.data.tpl_dc3_front_id !== undefined) {
            activeButton.dataset.dc3Front = data.data.tpl_dc3_front_id || "";
          }
          if (data.data.tpl_dc3_back_id !== undefined) {
            activeButton.dataset.dc3Back = data.data.tpl_dc3_back_id || "";
          }
          if (data.data.tpl_cproem_id !== undefined) {
            activeButton.dataset.cproemTpl = data.data.tpl_cproem_id || "";
          }
          if (data.data.tpl_diploma_id !== undefined) {            // >>> NUEVO
            activeButton.dataset.diplomaTpl = data.data.tpl_diploma_id || "";
          }
        }

        showAlert("success", data.message || "Programa actualizado correctamente.");
        closeModal();
      } catch (err) {
        console.error(err);
        showAlert(
          "error",
          "Ocurrió un error de conexión al guardar el programa. Intenta de nuevo."
        );
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initProgramEditModal);
  } else {
    initProgramEditModal();
  }
})();
