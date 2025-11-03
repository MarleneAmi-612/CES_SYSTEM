// admin_home.js — menú de usuario + modales (logout, perfil, cambio password, alta admin) + filas clicables
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
    if (openLogout) openLogout.addEventListener("click", function(e){ e.preventDefault(); menu && menu.classList.remove("open"); openModal("#logoutModal"); });
    var logoutClose = document.getElementById("logoutClose");
    if (logoutClose) logoutClose.addEventListener("click", function(){ closeModal("#logoutModal"); });
    var logoutCancel = document.getElementById("logoutCancel");
    if (logoutCancel) logoutCancel.addEventListener("click", function(){ closeModal("#logoutModal"); });
    var logoutBackdrop = document.getElementById("logoutBackdrop");
    if (logoutBackdrop) logoutBackdrop.addEventListener("click", function(){ closeModal("#logoutModal"); });
    var logoutConfirm = document.getElementById("logoutConfirm");
    if (logoutConfirm) logoutConfirm.addEventListener("click", function () {
      logoutConfirm.disabled = true;
      logoutForm.submit();
    });

    /* ---------- Modal Perfil ---------- */
    var profileLink = document.getElementById("profileLink");
    if (profileLink) profileLink.addEventListener("click", function(e){ e.preventDefault(); menu && menu.classList.remove("open"); openModal("#profileModal"); });

    /* ---------- Modal Cambiar Password (inline) ---------- */
    var pwdLink = document.getElementById("pwdInlineLink");
    if (pwdLink) pwdLink.addEventListener("click", function(e){ e.preventDefault(); menu && menu.classList.remove("open"); openModal("#pwdModal"); });

    var pwdForm = document.getElementById("pwdForm");
    if (pwdForm) {
      pwdForm.addEventListener("submit", function(e){
        e.preventDefault();
        submitForm(pwdForm, document.getElementById("pwdMsg"), function(){
          closeModal("#pwdModal");
        });
      });
    }

    /* ---------- Modal Agregar Usuario (admin) ---------- */
    var addUserOpen = document.getElementById("addUserOpen");
    if (addUserOpen) addUserOpen.addEventListener("click", function(e){ e.preventDefault(); menu && menu.classList.remove("open"); openModal("#addUserModal"); });

    // sugerencia de username a partir del correo
    var auEmail = document.getElementById("au_email");
    var auUsername = document.getElementById("au_username");
    if (auEmail && auUsername) {
      auEmail.addEventListener("input", function(){
        var v = (auEmail.value || "").split("@")[0].toLowerCase().replace(/[^a-z0-9_-]+/g,"");
        if (!auUsername.value) auUsername.value = v;
      });
    }

    var addUserForm = document.getElementById("addUserForm");
    if (addUserForm) {
      addUserForm.addEventListener("submit", function(e){
        e.preventDefault();
        submitForm(addUserForm, document.getElementById("auMsg"), function(){
          // limpiar y dejar abierto por si agregas más
          addUserForm.reset();
          var msg = document.getElementById("auMsg");
          if (msg) {
            msg.className = "form-msg ok";
            msg.textContent = "Usuario creado con éxito.";
          }
        });
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
      .then(function(r){ return r.json().then(function(d){ return {ok:r.ok, data:d}; }); })
      .then(function(res){
        if (res.ok && res.data && res.data.ok) {
          if (msgEl){ msgEl.className = "form-msg ok"; msgEl.textContent = "Guardado correctamente."; }
          if (typeof onSuccess === "function"){ setTimeout(onSuccess, 700); }
        } else {
          var err = (res.data && res.data.error) ? res.data.error : "Error al guardar.";
          if (msgEl){ msgEl.className = "form-msg err"; msgEl.textContent = err; }
        }
      })
      .catch(function(){
        if (msgEl){ msgEl.className = "form-msg err"; msgEl.textContent = "Error de red. Intenta de nuevo."; }
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
