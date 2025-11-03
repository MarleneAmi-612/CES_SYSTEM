// static/js/tracking-resend.js
(function () {
  const root = document.getElementById("trackingRoot");
  if (!root) return;

  const btn = document.getElementById("btnResend");
  if (!btn) return;

  const resendUrl   = root.getAttribute("data-resend-url");
  const redirectUrl = root.getAttribute("data-redirect-url") || "/";
  const csrf        = document.querySelector('meta[name="csrf-token"]')?.content || "";

  function showBlockingModal(seconds = 10) {
    // crea overlay modal
    let ov = document.getElementById("resendOverlay");
    if (ov) ov.remove();

    ov = document.createElement("div");
    ov.id = "resendOverlay";
    ov.className = "overlay";
    ov.innerHTML = `
      <div class="overlay__backdrop" aria-hidden="true"></div>
      <div class="overlay__dialog" role="dialog" aria-modal="true" aria-live="assertive">
        <div class="overlay__icon" aria-hidden="true">✅</div>
        <h3 class="overlay__title">¡Solicitud reenviada!</h3>
        <p class="overlay__text">
          Tu solicitud volvió a la etapa <strong>Pendiente</strong>. 
          Serás redirigido al inicio en <strong id="redirCount">${seconds}</strong> segundos…
        </p>
      </div>
    `;
    document.body.appendChild(ov);
    // bloquea scroll/interacción
    document.body.style.overflow = "hidden";

    // simple “focus trap” (en este modal no hay controles)
    ov.tabIndex = -1;
    ov.focus();

    // countdown + redirect
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
          "X-CSRFToken": csrf
        },
        credentials: "same-origin"
      });
      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        // en caso de error, también bloqueamos con aviso
        showBlockingModal(10);
        const title = document.querySelector("#resendOverlay .overlay__title");
        const text  = document.querySelector("#resendOverlay .overlay__text");
        const icon  = document.querySelector("#resendOverlay .overlay__icon");
        if (title) title.textContent = "No se pudo reenviar";
        if (text)  text.innerHTML = (data.msg || "Ocurrió un problema. Redirigiendo al inicio…") +
                                    ` <strong id="redirCount">10</strong>`;
        if (icon)  icon.textContent = "⚠️";
        return;
      }

      // éxito: actualiza chip visualmente y muestra modal bloqueante
      const tag = document.getElementById("statusTag");
      if (tag) { tag.className = "tag pending"; tag.textContent = "Pendiente"; }

      showBlockingModal(10);

    } catch (e) {
      showBlockingModal(10);
      const title = document.querySelector("#resendOverlay .overlay__title");
      const text  = document.querySelector("#resendOverlay .overlay__text");
      const icon  = document.querySelector("#resendOverlay .overlay__icon");
      if (title) title.textContent = "Error de red";
      if (text)  text.innerHTML = "No fue posible contactar al servidor. Redirigiendo al inicio en <strong id='redirCount'>10</strong> segundos…";
      if (icon)  icon.textContent = "🌐";
    }
  }

  btn.addEventListener("click", function (ev) {
    ev.preventDefault();
    resend();
  });
})();
