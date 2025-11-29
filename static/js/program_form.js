"use strict";

document.addEventListener("DOMContentLoaded", function () {
  // --- Diploma ---
  const comboDiploma   = document.getElementById("tpl_diploma_combined");
  const hiddenDipDesign = document.getElementById("plantilla_diploma");
  const hiddenDipDocx   = document.getElementById("docx_tpl_diploma");

  if (comboDiploma && hiddenDipDesign && hiddenDipDocx) {
    // Inicializar selección combinada según lo que venga guardado
    const currentDesignId = hiddenDipDesign.value;
    const currentDocxId   = hiddenDipDocx.value;

    if (currentDocxId) {
      const opt = comboDiploma.querySelector(
        'option[data-src="docx"][data-id="' + currentDocxId + '"]'
      );
      if (opt) opt.selected = true;
    } else if (currentDesignId) {
      const opt = comboDiploma.querySelector(
        'option[data-src="design"][data-id="' + currentDesignId + '"]'
      );
      if (opt) opt.selected = true;
    }

    // Al cambiar, actualizar los hidden
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

  // --- Constancia ---
  const constanciaType    = document.getElementById("constancia_type");
  const comboConstancia   = document.getElementById("tpl_constancia_combined");
  const hiddenConstDesign = document.getElementById("plantilla_constancia");
  const hiddenDc3         = document.getElementById("docx_tpl_dc3");
  const hiddenCproem      = document.getElementById("docx_tpl_cproem");

  function syncCombinedFromHidden() {
    if (!constanciaType || !comboConstancia) return;
    const t = (constanciaType.value || "").toLowerCase();

    // Reset selección
    comboConstancia.value = "";

    if (t === "dc3" && hiddenDc3 && hiddenDc3.value) {
      const opt = comboConstancia.querySelector(
        'option[data-src="docx_dc3"][data-id="' + hiddenDc3.value + '"]'
      );
      if (opt) opt.selected = true;
    } else if (t === "cproem" && hiddenCproem && hiddenCproem.value) {
      const opt = comboConstancia.querySelector(
        'option[data-src="docx_cproem"][data-id="' + hiddenCproem.value + '"]'
      );
      if (opt) opt.selected = true;
    } else if (hiddenConstDesign && hiddenConstDesign.value) {
      const opt = comboConstancia.querySelector(
        'option[data-src="design"][data-id="' + hiddenConstDesign.value + '"]'
      );
      if (opt) opt.selected = true;
    }
  }

  function filterConstanciaOptions() {
    if (!constanciaType || !comboConstancia) return;
    const t = (constanciaType.value || "").toLowerCase();

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

    // Si la opción seleccionada quedó oculta, limpiar
    const current = comboConstancia.options[comboConstancia.selectedIndex];
    if (current && current.hidden) {
      comboConstancia.value = "";
    }
  }

  if (constanciaType && comboConstancia && hiddenConstDesign && hiddenDc3 && hiddenCproem) {
    // Inicializar
    filterConstanciaOptions();
    syncCombinedFromHidden();

    // Cambio de tipo de constancia
    constanciaType.addEventListener("change", function () {
      // Al cambiar tipo, limpiamos hidden y selección para evitar incoherencias
      hiddenConstDesign.value = "";
      hiddenDc3.value = "";
      hiddenCproem.value = "";
      comboConstancia.value = "";
      filterConstanciaOptions();
    });

    // Cambio de selección combinada
    comboConstancia.addEventListener("change", function () {
      const opt = comboConstancia.options[comboConstancia.selectedIndex];

      hiddenConstDesign.value = "";
      hiddenDc3.value = "";
      hiddenCproem.value = "";

      if (!opt || !opt.value) return;

      const src = opt.getAttribute("data-src");
      const id  = opt.getAttribute("data-id") || "";
      const t   = (constanciaType.value || "").toLowerCase();

      if (src === "design") {
        hiddenConstDesign.value = id;
      } else if (src === "docx_dc3") {
        hiddenDc3.value = id;
        // por si acaso, aseguramos tipo
        if (constanciaType && t !== "dc3") constanciaType.value = "dc3";
      } else if (src === "docx_cproem") {
        hiddenCproem.value = id;
        if (constanciaType && t !== "cproem") constanciaType.value = "cproem";
      }
    });
  }
});
