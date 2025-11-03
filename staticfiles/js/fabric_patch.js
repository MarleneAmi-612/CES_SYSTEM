// static/js/fabric_patch.js
// Parche pequeño: si alguna lib asigna "alphabetical", lo mapeamos a "alphabetic"
// para evitar los warnings del navegador. Cargar DESPUÉS de fabric.min.js.
(function () {
  try {
    const proto = (window.CanvasRenderingContext2D || {}).prototype;
    if (!proto) return;

    const desc = Object.getOwnPropertyDescriptor(proto, "textBaseline");
    if (desc && typeof desc.set === "function") {
      const origSet = desc.set;
      Object.defineProperty(proto, "textBaseline", {
        configurable: true,
        enumerable: desc.enumerable,
        get: desc.get,
        set(v) {
          if (v === "alphabetical") v = "alphabetic";
          return origSet.call(this, v);
        }
      });
    } else {
      // Fallback ultra-defensivo por si no existe descriptor (muy raro en navegadores modernos)
      const _key = "__patched_textBaseline";
      Object.defineProperty(proto, "textBaseline", {
        configurable: true,
        enumerable: true,
        get() { return this[_key] || "alphabetic"; },
        set(v) { this[_key] = (v === "alphabetical") ? "alphabetic" : v; }
      });
    }
  } catch (e) {
    // Silencioso: si algo falla, no rompemos el editor
    console && console.debug && console.debug("fabric_patch.js: no-op", e);
  }
})();
