(function () {
  // ---------- CSRF helpers ----------
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    return getCookie('csrftoken');
  }

  async function postForm(url, formData) {
    const csrf = getCsrfToken();
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
      body: formData,
      credentials: 'same-origin'
    });
    if (!res.ok) {
      let msg = `Error HTTP ${res.status}`;
      try { const t = await res.text(); if (t) msg += `: ${t}`; } catch {}
      throw new Error(msg);
    }
    return res.json().catch(() => ({}));
  }

  function activeTipo() {
    const dipl = document.querySelector('#tabDiploma');
    return dipl && dipl.classList.contains('is-active') ? 'diploma' : 'constancia';
  }

  // ---------- Elementos base ----------
  const root = document.getElementById('egRoot');
  if (!root) return;

  const constKind   = (root.dataset.constKind || 'dc3').toLowerCase(); // 'dc3' | 'cproem'
  const previewUrl  = root.dataset.previewUrl;
  const downloadUrl = root.dataset.downloadUrl;
  const sendUrl     = root.dataset.sendUrl;
  const confirmUrl  = root.dataset.confirmUrl;
  const editUrl     = root.dataset.editUrl;

  try {
    console.log('[Egresados] constKind detectado =', constKind);
  } catch {}

  // ---------- Tabs documento (Diploma / Constancia) ----------
  const docTabs   = document.querySelectorAll('.segmented[data-scope="doc"] .segmented__btn');
  const docPanels = document.querySelectorAll('.doc-tab');

  function setDocTab(targetSel) {
    docTabs.forEach(b => b.classList.remove('is-active'));
    docPanels.forEach(p => p.classList.remove('is-active'));

    const btn = Array.from(docTabs).find(b => b.dataset.target === targetSel);
    const panel = document.querySelector(targetSel);
    if (btn) btn.classList.add('is-active');
    if (panel) panel.classList.add('is-active');
  }

  docTabs.forEach(btn => {
    btn.addEventListener('click', () => {
      setDocTab(btn.dataset.target);
    });
  });

  // Cambio automático a "Constancia" si el programa es CPROEM
  if (constKind === 'cproem') setDocTab('#tabConstancia');

  // También permite activar por query ?tab=constancia | diploma
  try {
    const params = new URLSearchParams(location.search);
    const tab = (params.get('tab') || '').toLowerCase();
    if (tab === 'constancia') setDocTab('#tabConstancia');
    else if (tab === 'diploma') setDocTab('#tabDiploma');
  } catch {}

  // ---------- Tabs sidebar (En proceso / Finalizados) ----------
  const sideTabs = document.querySelectorAll('.segmented[data-scope="side"] .segmented__btn');
  const panelInProcess = document.getElementById('panelInProcess');
  const panelFinished  = document.getElementById('panelFinished');

  function setSideTab(targetSel) {
    sideTabs.forEach(b => b.classList.toggle('is-active', b.dataset.target === targetSel));
    if (panelInProcess) {
      panelInProcess.classList.toggle('is-hidden', targetSel !== '#panelInProcess');
    }
    if (panelFinished) {
      panelFinished.classList.toggle('is-hidden', targetSel !== '#panelFinished');
    }
  }

  sideTabs.forEach(btn => {
    btn.addEventListener('click', () => {
      setSideTab(btn.dataset.target);
    });
  });

  // estado inicial: En proceso
  setSideTab('#panelInProcess');

  // ---------- Sidebar pagination (para ambas listas) ----------
  function setupPager(listEl, dotsEl) {
    if (!listEl) return;

    // Solo paginamos li.card
    const items = Array.from(listEl.querySelectorAll('li.card'));
    if (!items.length) {
      if (dotsEl) dotsEl.innerHTML = '';
      return;
    }

    let pageSize = parseInt(listEl.dataset.pageSize || '0', 10);
    if (!pageSize || pageSize <= 0) {
      pageSize = items.length; // si no hay pageSize válido, todo en una página
    }

    // Si todos caben en una sola página: no ocultes nada ni muestres dots
    if (items.length <= pageSize) {
      items.forEach(el => el.classList.remove('is-hidden'));
      if (dotsEl) dotsEl.innerHTML = '';
      return;
    }

    const pages = Math.ceil(items.length / pageSize);

    function render(page) {
      items.forEach((el, i) => {
        const p = Math.floor(i / pageSize);
        el.classList.toggle('is-hidden', p !== page);
      });

      if (dotsEl) {
        dotsEl.querySelectorAll('button').forEach((b, i) =>
          b.classList.toggle('is-active', i === page)
        );
      }
    }

    if (dotsEl) {
      dotsEl.innerHTML = '';
      for (let i = 0; i < pages; i++) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'dotpager__dot' + (i === 0 ? ' is-active' : '');
        b.addEventListener('click', () => render(i));
        dotsEl.appendChild(b);
      }
    }

    render(0);
  }

  setupPager(
    document.getElementById('inProcessList'),
    document.getElementById('inProcessDots')
  );
  setupPager(
    document.getElementById('finishedList'),
    document.getElementById('finishedDots')
  );

  // ---------- Preview (abre nueva pestaña) ----------
  const btnPrevDipl = document.getElementById('btnPrevDiploma');
  const btnPrevConst = document.getElementById('btnPrevConst');
  if (btnPrevDipl) {
    btnPrevDipl.addEventListener('click', (e) => {
      if (!previewUrl) return;
      e.preventDefault();
      const url = previewUrl + (previewUrl.includes('?') ? '&' : '?') + 'tipo=diploma';
      window.open(url, '_blank', 'noopener');
    });
  }
  if (btnPrevConst) {
    btnPrevConst.addEventListener('click', (e) => {
      if (!previewUrl) return;
      e.preventDefault();
      const url = previewUrl + (previewUrl.includes('?') ? '&' : '?') + 'tipo=constancia';
      window.open(url, '_blank', 'noopener');
    });
  }

  // ---------- Enviar por correo (diploma) ----------
  const sendDipl = document.getElementById('btnSendDiploma');
  if (sendDipl) {
    sendDipl.addEventListener('click', async () => {
      if (!sendUrl) return;
      sendDipl.disabled = true;
      try {
        const fd = new FormData();
        fd.append('tipo', 'diploma');
        const data = await postForm(sendUrl, fd);

        if (data && data.verify_url) {
          openDiplomaAlert(data.verify_url);
        } else {
          openDiplomaAlert(null);
        }
      } catch (e) {
        console.error(e);
        alert('No se pudo enviar el diploma.\n' + e.message);
      } finally {
        sendDipl.disabled = false;
      }
    });
  }

  // ---------- Confirmar constancia (publica token) ----------
  const chkConfirm = document.getElementById('chkConfirm');
  const btnConfirm = document.getElementById('btnConfirm');
  if (chkConfirm && btnConfirm) {
    chkConfirm.addEventListener('change', () => btnConfirm.disabled = !chkConfirm.checked);
    btnConfirm.addEventListener('click', async () => {
      if (!confirmUrl || !chkConfirm.checked) return;
      btnConfirm.disabled = true;
      try {
        const fd = new FormData(); fd.append('tipo', 'constancia');
        const data = await postForm(confirmUrl, fd);
        if (data && data.verify_url) alert('Constancia publicada. Verificación: ' + data.verify_url);
      } catch (e) {
        console.error(e); alert('No se pudo confirmar la constancia.\n' + e.message);
      } finally { btnConfirm.disabled = false; }
    });
  }

  // ---------- Modal Descarga ----------
  const dlModal  = document.getElementById('dlModal');
  const dlForm   = document.getElementById('dlForm');
  const dlCancel = document.getElementById('dlCancel');
  const dlSubmit = document.getElementById('dlSubmit');

  function openDlModal() {
    if (!dlModal) return;
    dlModal.hidden = false;
    setTimeout(() => {
      const first = dlForm?.querySelector('input[name="fmt"]') || dlSubmit;
      first && first.focus();
    }, 0);
    document.body.classList.add('no-scroll');
  }
  function closeDlModal() {
    if (!dlModal) return;
    dlModal.hidden = true;
    document.body.classList.remove('no-scroll');
  }
  if (dlCancel) dlCancel.addEventListener('click', closeDlModal);
  if (dlModal) dlModal.addEventListener('click', (e) => { if (e.target === dlModal) closeDlModal(); });

  const downDipl = document.getElementById('btnDownDiploma');
  const downConst = document.getElementById('btnDownConst');
  if (downDipl)  downDipl.addEventListener('click', () => openDlModal());
  if (downConst) downConst.addEventListener('click', () => openDlModal());

  if (dlForm) {
    dlForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!downloadUrl) return;
      const fmt = dlForm.querySelector('input[name="fmt"]:checked')?.value || 'pdf';
      const tipo = activeTipo();
      const url = downloadUrl
        + (downloadUrl.includes('?') ? '&' : '?')
        + 'tipo=' + encodeURIComponent(tipo)
        + '&fmt=' + encodeURIComponent(fmt);
      window.location.href = url;
      closeDlModal();
    });
  }

  // ---------- Mini dropdown Editar datos ----------
  const mini = document.querySelector('.mini-dd');
  const editBtn = document.getElementById('editToggle');
  const editMenu = document.getElementById('editPanel');
  const editClose = document.getElementById('editCloseBtn');
  const editSave = document.getElementById('editSaveBtn');
  const editForm = document.getElementById('editForm');

  function ddOpen(open) {
    if (!mini || !editMenu) return;
    mini.classList.toggle('is-open', !!open);
    editMenu.setAttribute('aria-hidden', open ? 'false' : 'true');
  }

  if (editBtn) editBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    ddOpen(!mini.classList.contains('is-open'));
  });
  if (editClose) editClose.addEventListener('click', () => ddOpen(false));
  document.addEventListener('click', (e) => { if (mini && !mini.contains(e.target)) ddOpen(false); });

  // ---------- Alerta (modal centrado) ----------
  const alertModal = document.getElementById('egAlert');
  const alertOk = document.getElementById('egAlertOk');
  const alertJson = document.getElementById('egAlertBody');

  function showAlert(changed) {
    if (!alertModal) return;
    const lines = Object.entries(changed || {}).map(([k,v]) => `• ${k}: ${v || '—'}`);
    alertJson.textContent = lines.length ? lines.join('\n') : 'No hubo cambios.';
    alertModal.hidden = false;
    document.body.classList.add('no-scroll');
    setTimeout(() => { window.location.reload(); }, 1600);
  }
  if (alertOk) alertOk.addEventListener('click', () => window.location.reload());

  // ---------- Guardar cambios (AJAX) ----------
  if (editSave && editForm && editUrl) {
    editSave.addEventListener('click', async () => {
      const fd = new FormData(editForm);
      editSave.disabled = true;
      try {
        const data = await postForm(editUrl, fd);
        if (!data.ok) throw new Error(data.msg || 'No se pudo guardar');
        ddOpen(false);
        showAlert(data.changed || {});
      } catch (e) {
        console.error(e);
        alert('No se pudo guardar.\n' + e.message);
        editSave.disabled = false;
      }
    });
  }

  // ---- Snippet CSP-friendly: cerrar con botón alterno (sin inline) ----
  document.addEventListener('DOMContentLoaded', function () {
    const alt = document.getElementById('editCloseBtnAlt');
    const mainClose = document.getElementById('editCloseBtn');
    if (alt && mainClose) {
      alt.addEventListener('click', () => mainClose.click());
    }
  });
})();

// ---------- Alerta "Diploma publicado" ----------
const diplAlert      = document.getElementById('egDiplomaAlert');
const diplAlertLink  = document.getElementById('egDiplomaAlertLink');
const diplAlertClose = document.getElementById('egDiplomaAlertClose');

function openDiplomaAlert(verifyUrl) {
  // Fallback: si por algo no existe el modal, al menos abrimos la URL
  if (!diplAlert) {
    if (verifyUrl) window.open(verifyUrl, '_blank', 'noopener');
    return;
  }

  if (diplAlertLink && verifyUrl) {
    diplAlertLink.href = verifyUrl;
  }

  diplAlert.hidden = false;
  document.body.classList.add('no-scroll');
}

if (diplAlertClose) {
  diplAlertClose.addEventListener('click', () => {
    diplAlert.hidden = true;
    document.body.classList.remove('no-scroll');
  });
}
