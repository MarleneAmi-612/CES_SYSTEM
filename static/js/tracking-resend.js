// static/js/tracking-resend.js
(function () {
  const root = document.getElementById("trackingRoot");
  if (!root) return;

  const btn = document.getElementById("btnResend");
  if (!btn) return;

  const resendUrl   = root.getAttribute("data-resend-url");
  const redirectUrl = root.getAttribute("data-redirect-url") || "/";

  // --- CSRF helpers ---
  function getCookie(name) {
    const v = `; ${document.cookie}`;
    const p = v.split(`; ${name}=`);
    if (p.length === 2) return p.pop().split(";").shift();
  }
  // 1) intenta <meta name="csrf-token" content="...">; 2) cae a cookie csrftoken
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return (meta && meta.content) ? meta.content : getCookie("csrftoken");
  }

  function showBlockingModal(seconds = 10, opts) {
    const { icon = "✅", title = "¡Solicitud reenviada!", text = null } = (opts || {});

    let ov = document.getElementById("resendOverlay");
    if (ov) ov.remove();

    ov = document.createElement("div");
    ov.id = "resendOverlay";
    ov.className = "overlay";
    ov.innerHTML = `
      <div class="overlay__backdrop" aria-hidden="true"></div>
      <div class="overlay__dialog" role="dialog" aria-modal="true" aria-live="assertive">
        <div class="overlay__icon" aria-hidden="true">${icon}</div>
        <h3 class="overlay__title">${title}</h3>
        <p class="overlay__text">
          ${text || `Tu solicitud volvió a la etapa <strong>Pendiente</strong>. 
          Serás redirigido al inicio en <strong id="redirCount">${seconds}</strong> segundos…`}
        </p>
      </div>
    `;
    document.body.appendChild(ov);
    document.body.style.overflow = "hidden";

    ov.tabIndex = -1;
    ov.focus();

    let remain = seconds;
    const span = ov.querySelector("#redirCount");
    const t = setInterval(() => {
      remain -= 1;
      if (span) span.textContent = String(remain);
      if (remain <= 0) {
        clearInterval(t);
        window.location.href = redirectUrl;
      }
    }, 1000);
  }

  async function resend() {
    try {
      const resp = await fetch(resendUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        credentials: "same-origin",
      });

      let data = {};
      try { data = await resp.json(); } catch (_) {}

      if (!resp.ok || !data.ok) {
        showBlockingModal(10, {
          icon: "⚠️",
          title: "No se pudo reenviar",
          text: `${(data && data.msg) ? data.msg : "Ocurrió un problema. Redirigiendo al inicio…"} <strong id="redirCount">10</strong>`,
        });
        return;
      }

      // éxito: actualiza chip y muestra modal
      const tag = document.getElementById("statusTag");
      if (tag) { tag.className = "tag pending"; tag.textContent = "Pendiente"; }

      showBlockingModal(10);
    } catch (e) {
      showBlockingModal(10, {
        icon: "🌐",
        title: "Error de red",
        text: "No fue posible contactar al servidor. Redirigiendo al inicio en <strong id='redirCount'>10</strong> segundos…",
      });
    }
  }

  btn.addEventListener("click", function (ev) {
    ev.preventDefault();
    resend();
  });
})();
