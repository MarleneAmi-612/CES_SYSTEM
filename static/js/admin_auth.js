(function(){
  var KEY = 'admin-theme';
  var root = document.documentElement;

  function currentTheme(){
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === 'light' || saved === 'dark') return saved;
    } catch(e){}
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  function applyTheme(t){
    root.setAttribute('data-theme', t);
    try { localStorage.setItem(KEY, t); } catch(e){}
    var btn = document.getElementById('themeToggle');
    var lbl = document.getElementById('themeLabel');
    if (lbl) lbl.textContent = (t === 'dark') ? 'Oscuro' : 'Claro';
    if (btn) btn.setAttribute('aria-pressed', (t === 'dark') ? 'true' : 'false');
  }

  // Inicializa tema lo antes posible
  applyTheme(currentTheme());

  // Listeners
  window.addEventListener('DOMContentLoaded', function(){
    var btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.addEventListener('click', function(){
      var now = (root.getAttribute('data-theme') === 'dark') ? 'light' : 'dark';
      applyTheme(now);
    });
  });
})();
