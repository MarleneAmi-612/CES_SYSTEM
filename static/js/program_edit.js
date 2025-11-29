/* ===========================================================
   program_edit.js – Modal de edición AJAX para programas
   Versión con plantillas combinadas (diseño + DOCX)
   =========================================================== */
"use strict";

(function () {
  const $  = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));

  // ------------------------------
  // Helpers
  // ------------------------------
  function getCSRFToken() {
    const el = document.querySelector("input[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  // Alerta bonita reutilizando los estilos .alert / .alert-stack
  function showToast(message, kind = "success") {
    // Si no existe el contenedor de alertas, lo creamos
    let stack = document.querySelector(".alert-stack");
    if (!stack) {
      stack = document.createElement("section");
      stack.className = "alert-stack";

      const page = document.querySelector(".page") || document.body;
      page.prepend(stack);
    }

    const alert = document.createElement("div");
    alert.className = `alert alert--${kind}`;

    alert.innerHTML = `
      <button type="button" class="alert__close" aria-label="Cerrar">&times;</button>
      <div class="alert__content">${message}</div>
      <div class="alert__progress"></div>
    `;

    const btnClose = alert.querySelector(".alert__close");
    const progress = alert.querySelector(".alert__progress");

    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      alert.classList.add("is-closing");
      setTimeout(() => {
        if (alert.parentNode) {
          alert.parentNode.removeChild(alert);
        }
      }, 200);
    };

    if (btnClose) {
      btnClose.addEventListener("click", close);
    }

    if (progress) {
      progress.style.transition = "width 4s linear";
      // empieza llena y se vacía en 4s
      requestAnimationFrame(() => {
        progress.style.width = "0%";
      });
    }

    stack.appendChild(alert);
    setTimeout(close, 4000);
  }

  // ------------------------------
  // Modal de edición
  // ------------------------------
  let modal,
      overlay,
      form,
      btnSave,
      inputId,
      inputCode,
      inputName,
      radiosConstancia,
      currentRow = null,
      currentUrl = null;

  // Plantillas diploma / constancia (combinadas)
  let comboDiploma,
      comboConstancia,
      hiddenDipDesign,
      hiddenDipDocx,
      hiddenConstDesign,
      hiddenDc3,
      hiddenCproem;

  function getConstanciaType() {
    if (!radiosConstancia) return "";
    const checked = radiosConstancia.find(r => r.checked);
    return checked ? (checked.value || "").toLowerCase() : "";
  }

  function initDiplomaFromValues(diplomaDesignId, diplomaDocxId) {
    if (!comboDiploma || !hiddenDipDesign || !hiddenDipDocx) return;

    hiddenDipDesign.value = diplomaDesignId || "";
    hiddenDipDocx.value   = diplomaDocxId || "";
    comboDiploma.value = "";

    if (diplomaDocxId) {
      const opt = comboDiploma.querySelector('option[data-src="docx"][data-id="' + diplomaDocxId + '"]');
      if (opt) opt.selected = true;
    } else if (diplomaDesignId) {
      const opt = comboDiploma.querySelector('option[data-src="design"][data-id="' + diplomaDesignId + '"]');
      if (opt) opt.selected = true;
    }
  }

  function filterConstanciaOptions() {
    if (!comboConstancia) return;
    const t = getConstanciaType();

    Array.from(comboConstancia.options).forEach(function (opt) {
      if (!opt.value) {
        opt.hidden = false;
        return;
      }
      const kind = (opt.getAttribute("data-kind") || "").toLowerCase();
      if (t === "dc3" || t === "cproem") {
        opt.hidden = (kind && kind !== t);
      } else {
        opt.hidden = false;
      }
    });

    const sel = comboConstancia.options[comboConstancia.selectedIndex];
    if (sel && sel.hidden) {
      comboConstancia.value = "";
    }
  }

  function initConstanciaFromValues(constDesignId, docxDc3Id, docxCproemId) {
    if (!comboConstancia || !hiddenConstDesign || !hiddenDc3 || !hiddenCproem) return;

    hiddenConstDesign.value = constDesignId || "";
    hiddenDc3.value         = docxDc3Id || "";
    hiddenCproem.value      = docxCproemId || "";

    const t = getConstanciaType();
    comboConstancia.value = "";

    if (t === "dc3" && docxDc3Id) {
      const opt = comboConstancia.querySelector('option[data-src="docx_dc3"][data-id="' + docxDc3Id + '"]');
      if (opt) opt.selected = true;
    } else if (t === "cproem" && docxCproemId) {
      const opt = comboConstancia.querySelector('option[data-src="docx_cproem"][data-id="' + docxCproemId + '"]');
      if (opt) opt.selected = true;
    } else if (constDesignId) {
      const opt = comboConstancia.querySelector('option[data-src="design"][data-id="' + constDesignId + '"]');
      if (opt) opt.selected = true;
    }
  }

  function openModalFromButton(btn) {
    if (!modal || !form) return;

    currentRow = btn.closest("tr");
    currentUrl = btn.dataset.url || "";

    const simId      = btn.dataset.id || "";
    const code       = btn.dataset.code || "";
    const name       = btn.dataset.name || "";
    const constancia = (btn.dataset.constancia || "cproem").toLowerCase();

    const diplomaDesignId = btn.dataset.diplomaDesign || btn.dataset.diplomaTpl || "";
    const diplomaDocxId   = btn.dataset.diplomaDocx   || "";
    const constDesignId   = btn.dataset.constDesign   || "";
    const docxDc3Id       = btn.dataset.docxDc3       || btn.dataset.dc3Front || "";
    const docxCproemId    = btn.dataset.docxCproem    || btn.dataset.cproemTpl || "";

    if (inputId)   inputId.value   = simId;
    if (inputCode) inputCode.value = code;
    if (inputName) inputName.value = name;

    if (radiosConstancia && radiosConstancia.length) {
      radiosConstancia.forEach((r) => {
        r.checked = (r.value.toLowerCase() === constancia);
      });
    }

    initDiplomaFromValues(diplomaDesignId, diplomaDocxId);
    filterConstanciaOptions();
    initConstanciaFromValues(constDesignId, docxDc3Id, docxCproemId);

    modal.classList.remove("is-hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");

    if (inputName) {
      inputName.focus();
      inputName.select();
    }
  }

  function closeModal() {
    if (!modal) return;

    modal.classList.add("is-hidden");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");

    currentRow = null;
    currentUrl = null;
  }

  function bindEditButtons() {
    document.addEventListener("click", function (ev) {
      const btn = ev.target.closest && ev.target.closest(".js-program-edit");
      if (!btn) return;

      ev.preventDefault();
      openModalFromButton(btn);
    });
  }

  function updateRow(simId, data) {
    let row = currentRow;
    if (!row || !row.isConnected) {
      row = document.querySelector(`tr[data-id="${simId}"]`);
    }
    if (!row) return;

    if (data.programa) {
      const codeCell = $(".js-col-code", row);
      if (codeCell) codeCell.textContent = data.programa;

      const editBtn = $(".js-program-edit", row);
      if (editBtn) editBtn.dataset.code = data.programa;
    }

    if (data.programa_full) {
      const nameCell = $(".js-col-name", row);
      if (nameCell) nameCell.textContent = data.programa_full;

      const editBtn = $(".js-program-edit", row);
      if (editBtn) editBtn.dataset.name = data.programa_full;
    }

    if (data.constancia) {
      const constCell = $(".js-col-constancia", row);
      if (constCell) constCell.textContent = data.constancia;

      const editBtn = $(".js-program-edit", row);
      if (editBtn) editBtn.dataset.constancia = data.constancia;
    }
  }

  async function handleSubmit() {
    if (!form || !inputCode || !inputName) return;

    const simId = inputId ? (inputId.value || "") : "";
    const code  = (inputCode.value || "").trim();
    const name  = (inputName.value || "").trim();

    let constancia = "cproem";
    if (radiosConstancia && radiosConstancia.length) {
      const checked = radiosConstancia.find((r) => r.checked);
      if (checked) {
        constancia = (checked.value || "cproem").toLowerCase();
      }
    }

    if (!code || !name) {
      showToast("Los campos «Programa» y «Nombre completo» son obligatorios.", "error");
      return;
    }

    if (!currentUrl) {
      console.error("No se encontró la URL de edición para este programa.");
      showToast("No se encontró la URL de edición para este programa.", "error");
      return;
    }

    const diplomaDesignId = hiddenDipDesign ? (hiddenDipDesign.value || "") : "";
    const diplomaDocxId   = hiddenDipDocx   ? (hiddenDipDocx.value   || "") : "";
    const constDesignId   = hiddenConstDesign ? (hiddenConstDesign.value || "") : "";
    const docxDc3Id       = hiddenDc3 ? (hiddenDc3.value || "") : "";
    const docxCproemId    = hiddenCproem ? (hiddenCproem.value || "") : "";

    const payload = {
      programa:      code,
      programa_full: name,
      constancia:    constancia,
      sim_id:        simId || null,

      diploma_design_id: diplomaDesignId || null,
      diploma_docx_id:   diplomaDocxId   || null,
      const_design_id:   constDesignId   || null,
      docx_dc3_id:       docxDc3Id       || null,
      docx_cproem_id:    docxCproemId    || null,
    };

    const csrftoken = getCSRFToken();

    if (btnSave) {
      btnSave.disabled = true;
      btnSave.textContent = "Guardando…";
    }

    try {
      const resp = await fetch(currentUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify(payload),
      });

      let data;
      try {
        data = await resp.json();
      } catch (e) {
        data = null;
      }

      if (!resp.ok || !data || !data.success) {
        const msg = (data && data.message) || "No se pudo guardar el programa.";
        console.error("Error al guardar programa:", data || resp.statusText);
        showToast(msg, "error");
        return;
      }

      updateRow(simId, data.data || {});
      showToast(data.message || "Programa actualizado correctamente.", "success");
      closeModal();
    } catch (err) {
      console.error("Error inesperado en AJAX:", err);
      showToast("Ocurrió un error de comunicación. Intenta de nuevo.", "error");
    } finally {
      if (btnSave) {
        btnSave.disabled = false;
        btnSave.textContent = "Guardar cambios";
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    modal  = document.getElementById("programEditModal");
    if (!modal) return;

    overlay = modal.querySelector(".modal__overlay");
    form    = document.getElementById("programEditForm");
    btnSave = document.getElementById("programEditSave");

    inputId   = document.getElementById("editId");
    inputCode = document.getElementById("editCode");
    inputName = document.getElementById("editName");

    radiosConstancia = $$("input[name='editConstancia']", modal);

    comboDiploma      = document.getElementById("editTplDiplomaCombined");
    comboConstancia   = document.getElementById("editTplConstanciaCombined");
    hiddenDipDesign   = document.getElementById("editDiplomaDesign");
    hiddenDipDocx     = document.getElementById("editDiplomaDocx");
    hiddenConstDesign = document.getElementById("editConstDesign");
    hiddenDc3         = document.getElementById("editDocxDc3");
    hiddenCproem      = document.getElementById("editDocxCproem");

    if (!form || !inputCode || !inputName) {
      console.warn("Modal de edición de programa incompleto; se desactiva JS de edición.");
      return;
    }

    if (overlay) {
      overlay.addEventListener("click", closeModal);
    }

    // Cerrar con cualquier elemento que tenga data-modal-close (overlay + botón Cancelar)
    const closeButtons = $$("[data-modal-close]", modal);
    closeButtons.forEach((btn) => {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        closeModal();
      });
    });


    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !modal.classList.contains("is-hidden")) {
        closeModal();
      }
    });

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      handleSubmit();
    });

    if (btnSave) {
      btnSave.addEventListener("click", function (ev) {
        ev.preventDefault();
        handleSubmit();
      });
    }

    // Cambio de tipo de constancia (radios)
    if (radiosConstancia && radiosConstancia.length && comboConstancia) {
      radiosConstancia.forEach((r) => {
        r.addEventListener("change", function () {
          if (hiddenConstDesign) hiddenConstDesign.value = "";
          if (hiddenDc3) hiddenDc3.value = "";
          if (hiddenCproem) hiddenCproem.value = "";
          comboConstancia.value = "";
          filterConstanciaOptions();
        });
      });

      filterConstanciaOptions();
    }

    if (comboDiploma && hiddenDipDesign && hiddenDipDocx) {
      comboDiploma.addEventListener("change", function () {
        const opt = comboDiploma.options[comboDiploma.selectedIndex];

        hiddenDipDesign.value = "";
        hiddenDipDocx.value   = "";

        if (!opt || !opt.value) return;

        const src = opt.getAttribute("data-src");
        const id  = opt.getAttribute("data-id") || "";

        if (src === "design") {
          hiddenDipDesign.value = id;
        } else if (src === "docx") {
          hiddenDipDocx.value = id;
        }
      });
    }

    if (comboConstancia && hiddenConstDesign && hiddenDc3 && hiddenCproem) {
      comboConstancia.addEventListener("change", function () {
        const opt = comboConstancia.options[comboConstancia.selectedIndex];

        hiddenConstDesign.value = "";
        hiddenDc3.value         = "";
        hiddenCproem.value      = "";

        if (!opt || !opt.value) return;

        const src = opt.getAttribute("data-src");
        const id  = opt.getAttribute("data-id") || "";
        const t   = (getConstanciaType() || "").toLowerCase();

        if (src === "design") {
          hiddenConstDesign.value = id;
        } else if (src === "docx_dc3") {
          hiddenDc3.value = id;
          if (t !== "dc3" && radiosConstancia && radiosConstancia.length) {
            const r = radiosConstancia.find(r => r.value.toLowerCase() === "dc3");
            if (r) r.checked = true;
          }
        } else if (src === "docx_cproem") {
          hiddenCproem.value = id;
          if (t !== "cproem" && radiosConstancia && radiosConstancia.length) {
            const r = radiosConstancia.find(r => r.value.toLowerCase() === "cproem");
            if (r) r.checked = true;
          }
        }
      });
    }

    bindEditButtons();
  });
})();
