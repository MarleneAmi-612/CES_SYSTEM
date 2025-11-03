// static/js/tracking-progress.js
(function () {
  function applyProgressFromAttr() {
    const bar = document.getElementById('progressLine');
    if (!bar) return;
    const val = parseInt(bar.dataset.progress || '0', 10);
    const pct = Number.isFinite(val) ? Math.max(0, Math.min(100, val)) : 0;
    bar.style.width = pct + '%';
  }
  window.applyProgressFromAttr = applyProgressFromAttr;
  document.addEventListener('DOMContentLoaded', applyProgressFromAttr);
})();
