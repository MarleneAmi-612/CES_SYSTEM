// admin_home.js — menú de usuario + modales + alta admin + filas clicables + orden de tabla en frontend
(function () {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function init() {
    /* ---------- Menú de usuario ---------- */
    var menuBtn = document.getElementById("userMenuBtn");
    var menu    = document.getElementById("userMenu");

    if (menuBtn && menu) {
      menuBtn.addEventListener("click", function () {
        var isOpen = menu.classList.toggle("open");
        menuBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
        if (isOpen) {
          var first = menu.querySelector('[role="menuitem"]');
          if (first) setTimeout(function(){ first.focus(); }, 10);
        }
      });

      document.addEventListener("click", function (e) {
        if (!menu.classList.contains("open")) return;
        if (!menu.contains(e.target) && !menuBtn.contains(e.target)) {
          menu.classList.remove("open");
          menuBtn.setAttribute("aria-expanded", "false");
        }
      });

      menu.addEventListener("keydown", function (e) {
        var items = Array.from(menu.querySelectorAll('[role="menuitem"]'));
        if (!items.length) return;

        var current = document.activeElement;
        var idx = items.indexOf(current);

        if (e.key === "Escape") {
          e.preventDefault();
          menu.classList.remove("open");
          menuBtn.setAttribute("aria-expanded","false");
          menuBtn.focus();
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          var next = items[(idx + 1 + items.length) % items.length];
          next && next.focus();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          var prev = items[(idx - 1 + items.length) % items.length];
          prev && prev.focus();
        }
      });
    }

    /* ---------- Utilidad: abrir/cerrar modales ---------- */
    function openModal(id){
      var m = document.querySelector(id);
      if (!m) return;
      m.classList.add("is-open");
      m.setAttribute("aria-hidden","false");
      m.setAttribute("aria-modal","true");
      document.body.style.overflow = "hidden";
      var primary = m.querySelector(".btn.btn--primary, [type='submit']");
      if (primary) setTimeout(function(){ primary.focus(); }, 10);
    }
    function closeModal(id){
      var m = document.querySelector(id);
      if (!m) return;
      m.classList.remove("is-open");
      m.setAttribute("aria-hidden","true");
      m.setAttribute("aria-modal","false");
      document.body.style.overflow = "";
      menuBtn && menuBtn.focus();
    }
    // permite data-close="#id"
    document.addEventListener("click", function(e){
      var t = e.target.closest("[data-close]");
      if (t) {
        e.preventDefault();
        closeModal(t.getAttribute("data-close"));
      }
    });

    /* ---------- Modal Logout ---------- */
    var openLogout = document.getElementById("logoutOpen");
    var logoutForm = document.getElementById("logoutForm");
    if (openLogout) openLogout.addEventListener("click", function(e){
      e.preventDefault();
      menu && menu.classList.remove("open");
      openModal("#logoutModal");
    });
    var logoutClose = document.getElementById("logoutClose");
    if (logoutClose) logoutClose.addEventListener("click", function(){
      closeModal("#logoutModal");
    });
    var logoutCancel = document.getElementById("logoutCancel");
    if (logoutCancel) logoutCancel.addEventListener("click", function(){
      closeModal("#logoutModal");
    });
    var logoutBackdrop = document.getElementById("logoutBackdrop");
    if (logoutBackdrop) logoutBackdrop.addEventListener("click", function(){
      closeModal("#logoutModal");
    });
    var logoutConfirm = document.getElementById("logoutConfirm");
    if (logoutConfirm) logoutConfirm.addEventListener("click", function () {
      logoutConfirm.disabled = true;
      logoutForm.submit();
    });

    /* ---------- Modal Perfil ---------- */
    var profileLink = document.getElementById("profileLink");
    if (profileLink) profileLink.addEventListener("click", function(e){
      e.preventDefault();
      menu && menu.classList.remove("open");
      openModal("#profileModal");
    });

    /* ---------- Modal Cambiar Password (inline) ---------- */
    var pwdLink = document.getElementById("pwdInlineLink");
    if (pwdLink) pwdLink.addEventListener("click", function(e){
      e.preventDefault();
      menu && menu.classList.remove("open");
      openModal("#pwdModal");
    });

    var pwdForm = document.getElementById("pwdForm");
    if (pwdForm) {
      pwdForm.addEventListener("submit", function(e){
        e.preventDefault();
        submitForm(
          pwdForm,
          document.getElementById("pwdMsg"),
          function(){
            closeModal("#pwdModal");
          }
        );
      });
    }

    /* ---------- Modal Agregar Usuario (admin) ---------- */
    var addUserOpen = document.getElementById("addUserOpen");
    if (addUserOpen) addUserOpen.addEventListener("click", function(e){
      e.preventDefault();
      menu && menu.classList.remove("open");
      openModal("#addUserModal");
    });

    // sugerencia de username a partir del correo
    var auEmail = document.getElementById("au_email");
    var auUsername = document.getElementById("au_username");
    if (auEmail && auUsername) {
      auEmail.addEventListener("input", function(){
        var v = (auEmail.value || "")
          .split("@")[0]
          .toLowerCase()
          .replace(/[^a-z0-9_-]+/g,"");
        if (!auUsername.value) auUsername.value = v;
      });
    }

    var addUserForm = document.getElementById("addUserForm");
    if (addUserForm) {
      addUserForm.addEventListener("submit", function(e){
        e.preventDefault();
        var msg = document.getElementById("auMsg");

        submitForm(addUserForm, msg, function(){
          // limpiar campos pero dejar la alerta visible
          addUserForm.reset();
          if (msg) {
            msg.className = "form-msg is-visible form-msg--ok";
            msg.innerHTML =
              "<span class='form-msg__icon' aria-hidden='true'>✔</span>" +
              "<span>Usuario creado con éxito.</span>";
          }
        });
      });
    }

    /* ---------- ORDENAR TABLA EN FRONTEND ---------- */
    var sortSelect = document.getElementById("order");
    var sortBtn    = document.getElementById("orderApplyBtn");
    var tbody      = document.getElementById("requestsBody");

    if (sortSelect && sortBtn && tbody) {
      // cacheamos las filas originales
      var rows = Array.from(tbody.querySelectorAll("tr.rowlink"));

      function sortTable(order) {
        var sorted = rows.slice();

        if (order === "date_asc" || order === "date_desc") {
          sorted.sort(function (a, b) {
            var da = new Date((a.getAttribute("data-sent-at") || "").replace(" ", "T"));
            var db = new Date((b.getAttribute("data-sent-at") || "").replace(" ", "T"));
            if (isNaN(da) || isNaN(db)) return 0;
            return (order === "date_asc") ? (da - db) : (db - da);
          });
        } else if (order === "name_asc" || order === "name_desc") {
          sorted.sort(function (a, b) {
            var na = (a.getAttribute("data-name") || "").toLowerCase();
            var nb = (b.getAttribute("data-name") || "").toLowerCase();
            if (na < nb) return (order === "name_asc") ? -1 : 1;
            if (na > nb) return (order === "name_asc") ? 1 : -1;
            return 0;
          });
        }

        // reinsertamos filas en el nuevo orden
        sorted.forEach(function (tr) {
          tbody.appendChild(tr);
        });
      }

      // botón aplicar
      sortBtn.addEventListener("click", function () {
        sortTable(sortSelect.value);
      });

      // también al cambiar el select
      sortSelect.addEventListener("change", function () {
        sortTable(sortSelect.value);
      });
    }

    /* ---------- Helper envío AJAX ---------- */
    function submitForm(form, msgEl, onSuccess){
      var fd = new FormData(form);
      var csrf = form.querySelector('input[name="csrfmiddlewaretoken"]');

      fetch(form.action, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrf ? csrf.value : ""
        },
        body: fd,
        credentials: "same-origin"
      })
      .then(function(r){
        return r.json().then(function(d){
          return { ok: r.ok, data: d };
        });
      })
      .then(function(res){
        if (!msgEl) return;

        if (res.ok && res.data && res.data.ok) {
          // ÉXITO
          msgEl.className = "form-msg is-visible form-msg--ok";
          msgEl.innerHTML =
            "<span class='form-msg__icon' aria-hidden='true'>✔</span>" +
            "<span>Guardado correctamente.</span>";

          if (typeof onSuccess === "function") {
            setTimeout(onSuccess, 700);
          }
        } else {
          // ERROR
          var err = (res.data && (res.data.error || res.data.msg))
            ? (res.data.error || res.data.msg)
            : "Error al guardar.";

          msgEl.className = "form-msg is-visible form-msg--err";
          msgEl.innerHTML =
            "<span class='form-msg__icon' aria-hidden='true'>⚠</span>" +
            "<span>" + err + "</span>";
        }
      })
      .catch(function(){
        if (!msgEl) return;
        msgEl.className = "form-msg is-visible form-msg--err";
        msgEl.innerHTML =
          "<span class='form-msg__icon' aria-hidden='true'>⚠</span>" +
          "<span>Error de red. Intenta de nuevo.</span>";
      });
    }

    /* ---------- ESC para cerrar modales ---------- */
    document.addEventListener("keydown", function (e) {
      var anyOpen = document.querySelector(".modal.is-open");
      if (!anyOpen) return;
      if (e.key === "Escape") {
        var id = "#" + anyOpen.id;
        closeModal(id);
      }
      if (anyOpen.id === "logoutModal" && e.key === "Enter") {
        e.preventDefault();
        var btn = document.getElementById("logoutConfirm");
        btn && btn.click();
      }
    });

    /* ---------- Filas clicables (reemplazo de onclick inline) ---------- */
    initRowLinks();
  }

  function initRowLinks() {
    var rows = document.querySelectorAll(".rowlink[data-href]");
    rows.forEach(function (row) {
      // Accesible: permite focus + Enter
      if (!row.hasAttribute("tabindex")) row.setAttribute("tabindex", "0");

      row.addEventListener("click", function (e) {
        // Evita navegación si el click fue en un control interactivo
        if (e.target.closest("a,button,summary,input,select,textarea,label")) return;
        var href = row.getAttribute("data-href");
        if (href) window.location.assign(href);
      });

      row.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          var href = row.getAttribute("data-href");
          if (href) window.location.assign(href);
        }
      });
    });
  }
})();
