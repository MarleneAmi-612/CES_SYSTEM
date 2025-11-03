(function () {
  const reqId = window.CES_REQ_ID;
  if (!reqId) return; // nada seleccionado

  const $tipoRadios = Array.from(document.querySelectorAll('input[name="tipo_doc"]'));
  const $formato = document.getElementById('formato');
  const $btnDownload = document.getElementById('btn-download');
  const $btnVer = document.getElementById('btn-ver');
  const $btnPublicar = document.getElementById('btn-publicar');
  const $btnConfirmar = document.getElementById('btn-confirmar');

  // Mapea selección visual -> query de backend
  function currentTipo() {
    const r = $tipoRadios.find(x => x.checked);
    if (!r) return 'diploma';
    return r.value; // 'diploma' | 'dc3' | 'cproem'
  }

  function resolveTipoForActions() {
    // Para acciones del backend mantenemos:
    // - diploma -> diploma
    // - dc3     -> constancia
    // - cproem  -> constancia
    const t = currentTipo();
    return (t === 'diploma') ? 'diploma' : 'constancia';
  }

  function updateDownloadHref() {
    const tipo = resolveTipoForActions();
    const fmt = $formato.value || 'pdf';
    $btnDownload.href = `/administracion/egresados/${reqId}/download/?tipo=${encodeURIComponent(tipo)}&fmt=${encodeURIComponent(fmt)}`;
  }

  // Eventos UI
  $tipoRadios.forEach(r => r.addEventListener('change', updateDownloadHref));
  $formato.addEventListener('change', updateDownloadHref);
  updateDownloadHref();

  // Vista previa: abre nueva pestaña usando el endpoint de preview
  if ($btnVer) {
    $btnVer.addEventListener('click', () => {
      const tipo = resolveTipoForActions();
      // tu preview acepta ?tipo=diploma|constancia
      const url = `/administracion/egresados/${reqId}/preview/?tipo=${encodeURIComponent(tipo)}`;
      window.open(url, '_blank', 'noopener');
    });
  }

  // Publicar
  if ($btnPublicar) {
    $btnPublicar.addEventListener('click', async () => {
      const tipo = resolveTipoForActions();
      try {
        const resp = await fetch(`/administracion/egresados/${reqId}/send/`, {
          method: 'POST',
          headers: {'X-CSRFToken': window.CES_CSRF},
          body: new URLSearchParams({tipo})
        });
        const data = await resp.json();
        if (data.ok) alert(`Publicado. URL verificación: ${data.verify_url}`);
        else alert(data.error || 'No se pudo publicar.');
      } catch (e) {
        alert('Error de red/publicación.');
      }
    });
  }

  // Confirmar (deja disponible para alumno)
  if ($btnConfirmar) {
    $btnConfirmar.addEventListener('click', async () => {
      const tipo = resolveTipoForActions();
      try {
        const resp = await fetch(`/administracion/egresados/${reqId}/confirm/`, {
          method: 'POST',
          headers: {'X-CSRFToken': window.CES_CSRF},
          body: new URLSearchParams({tipo})
        });
        const data = await resp.json();
        if (data.ok) alert('Confirmado y disponible.');
        else alert(data.error || 'No se pudo confirmar.');
      } catch (e) {
        alert('Error de red/confirmación.');
      }
    });
  }
})();
