// static/js/nice-select.js
(() => {
  function create(el) {
    const select = typeof el === "string" ? document.querySelector(el) : el;
    if (!select || select.dataset._cesNice) return;
    select.dataset._cesNice = "1";

    // Contenedor
    const wrap = document.createElement("div");
    wrap.className = "ns-wrap";
    wrap.setAttribute("role", "combobox");
    wrap.setAttribute("aria-haspopup", "listbox");
    wrap.setAttribute("aria-expanded", "false");

    // Botón visible
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ns-btn";
    const current = document.createElement("span");
    current.className = "ns-current";
    current.textContent = select.options[select.selectedIndex]?.text || select.getAttribute("placeholder") || "Selecciona";
    const chev = document.createElement("span");
    chev.className = "ns-chev";
    btn.append(current, chev);

    // Lista
    const list = document.createElement("div");
    list.className = "ns-list";
    list.setAttribute("role", "listbox");
    list.tabIndex = -1;

    // Opciones
    [...select.options].forEach((opt, i) => {
      const item = document.createElement("div");
      item.className = "ns-item";
      item.setAttribute("role", "option");
      item.dataset.value = opt.value;
      item.textContent = opt.textContent;
      if (opt.disabled) { item.classList.add("is-disabled"); }
      if (opt.selected) { item.classList.add("is-selected"); }
      item.addEventListener("click", () => {
        if (opt.disabled) return;
        select.value = opt.value;
        current.textContent = opt.textContent;
        list.querySelectorAll(".ns-item.is-selected").forEach(el => el.classList.remove("is-selected"));
        item.classList.add("is-selected");
        close();
        // Dispara change por si lo usas en views/forms
        select.dispatchEvent(new Event("change", { bubbles: true }));
      });
      list.appendChild(item);
    });

    // Inserta
    select.style.display = "none";
    const parent = select.parentNode;
    parent.insertBefore(wrap, select);
    wrap.append(btn, list);
    wrap.appendChild(select); // mantenemos el select en el DOM para el POST

    function open() {
      wrap.setAttribute("aria-expanded", "true");
      wrap.classList.add("is-open");
      document.addEventListener("click", onDoc, { once: true });
      list.focus();
    }
    function close() {
      wrap.setAttribute("aria-expanded", "false");
      wrap.classList.remove("is-open");
    }
    function onDoc(e) {
      if (!wrap.contains(e.target)) close();
    }

    btn.addEventListener("click", () => (wrap.classList.contains("is-open") ? close() : open()));

    // Teclado
    wrap.addEventListener("keydown", (e) => {
      const items = [...list.querySelectorAll(".ns-item:not(.is-disabled)")];
      const selIdx = items.findIndex(n => n.classList.contains("is-selected"));
      if (e.key === "ArrowDown") {
        e.preventDefault();
        const next = items[Math.min(selIdx + 1, items.length - 1)];
        if (next) next.click();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        const prev = items[Math.max(selIdx - 1, 0)];
        if (prev) prev.click();
      } else if (e.key === "Enter" || e.key === "Escape") {
        e.preventDefault();
        close();
        btn.focus();
      } else if (/^[a-z0-9]$/i.test(e.key)) {
        // búsqueda por primera letra
        const k = e.key.toLowerCase();
        const found = items.find(n => n.textContent.trim().toLowerCase().startsWith(k));
        if (found) found.click();
      }
    });
  }

  function enhance(selectorOrEl) {
    if (!selectorOrEl) {
      document.querySelectorAll("select[data-nice-select]").forEach(create);
    } else if (typeof selectorOrEl === "string") {
      document.querySelectorAll(selectorOrEl).forEach(create);
    } else {
      create(selectorOrEl);
    }
  }

  window.CESNiceSelect = { enhance };
})();
