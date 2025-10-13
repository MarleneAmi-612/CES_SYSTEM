(function () {
  const feed = document.getElementById("historyFeed");
  const root = document.getElementById("trackingRoot");
  if (!feed || !root) return;

  const pollUrl = root.dataset.pollUrl;
  if (!pollUrl) return;

  // ========= Estado -> textos y tipo de color =========
  const statusMap = {
    pending:    { title: "Solicitud enviada",         sub: "Estamos procesando tu solicitud.",              kind: "ok",   pos: 1 },
    review:     { title: "Tu solicitud está en revisión.", sub: "Te avisaremos por correo cuando sea aprobada.", kind: "info", pos: 2 },
    accepted:   { title: "¡Aprobada!",                sub: "Estamos preparando tu documento.",             kind: "ok",   pos: 3 },
    generating: { title: "Generando documento…",      sub: "Puede tardar unos dias.",                   kind: "info", pos: 4 },
    emailed:    { title: "Documento enviado por correo.", sub: "Revisa tu bandeja de entrada.",            kind: "info", pos: 5 },
    downloaded: { title: "Documento descargado.",     sub: "¡Listo! Guarda tu archivo.",                  kind: "ok",   pos: 6 },
    rejected:   { title: "Solicitud rechazada",       sub: "Se registró un rechazo.",                      kind: "bad",  pos: 3 }, // se corta en el 3
  };

  // ========= DOM refs =========
  const liveTitle = document.getElementById("liveTitle");
  const liveSub   = document.getElementById("liveSub");
  const liveTime  = document.getElementById("liveTime");
  const statusTag = document.getElementById("statusTag");
  const progress  = document.getElementById("progressLine");
  const stepEls   = Array.from(document.querySelectorAll(".stepper .step"));

  // ========= Estado previo para evitar duplicados =========
  let lastStatus   = feed.dataset.currentStatus || "";
  let lastCount    = parseInt(feed.dataset.events || "0", 10);
  let lastEventIso = null;

  // ========= Utilidades de formato =========
  const fmtDay  = new Intl.DateTimeFormat("es-MX", { weekday:"long", day:"2-digit", month:"long", year:"numeric" });
  const fmtTime = new Intl.DateTimeFormat("es-MX", { hour:"2-digit", minute:"2-digit", hour12:false });

  const dayTitle = d => fmtDay.format(d); // CSS capitaliza

  // ========= Stepper & progreso =========
  function updateStatusTag(status) {
    if (!statusTag) return;
    statusTag.className = "tag " + status;
    // Texto del tag
    const text =
      status === "pending"    ? "Pendiente" :
      status === "review"     ? "Revisión" :
      status === "accepted"   ? "Aprobada" :
      status === "generating" ? "Generando" :
      status === "emailed"    ? "Enviada por correo" :
      status === "downloaded" ? "Descargada" :
      status === "rejected"   ? "Rechazada" : (status || "");
    statusTag.textContent = text;
  }

  function updateStepper(status) {
    const meta = statusMap[status] || statusMap.pending;
    const total = stepEls.length; // normalmente 6
    const pos   = meta.pos;       // 1..6 (o 3 para rejected)

    // Restaurar textos originales de labels (usando data-title del HTML)
    stepEls.forEach((step) => {
      step.classList.remove("done","current","bad");
      const label = step.querySelector(".label");
      if (label && label.dataset.title) label.textContent = label.dataset.title;
    });

    if (status === "rejected") {
      // 1..3 rojos y renombramos paso 3
      stepEls.forEach((s, i) => { if (i <= 2) s.classList.add("bad","current","done"); });
      const step3Label = stepEls[2]?.querySelector(".label");
      if (step3Label) step3Label.textContent = "Solicitud rechazada";
    } else {
      // normales: 1..pos en naranja
      stepEls.forEach((s, i) => {
        if (i < pos) s.classList.add("done","current");
      });
    }

    // Progreso (0..100) sin style inline inicial; lo ponemos aquí
    if (progress) {
      const pct = total > 1 ? ((pos - 1) / (total - 1)) * 100 : 0;
      progress.style.width = Math.max(0, Math.min(100, pct)) + "%";
    }
  }

  // ========= Construcción de ítems de historial =========
  function applyKind(row, kind) {
    row.classList.remove("ok","bad","info");
    row.classList.add(kind || "info");
  }

  function buildItem({ kind, title, sub, whenDate, isCurrent }) {
    const item = document.createElement("div");
    item.className = "item " + (kind || "info") + (isCurrent ? " is-current" : "");

    const spine = document.createElement("div"); spine.className = "it-spine";
    const dot   = document.createElement("div"); dot.className = "it-dot";
    const time  = document.createElement("div"); time.className = "it-time";
    time.textContent = fmtTime.format(whenDate);

    const main  = document.createElement("div"); main.className = "it-main";
    const ttl   = document.createElement("div"); ttl.className = "it-title " + (kind || "info");
    ttl.textContent = title;
    main.appendChild(ttl);

    if (sub) {
      const subEl = document.createElement("div");
      subEl.className = "it-sub"; subEl.textContent = sub;
      main.appendChild(subEl);
    }

    item.append(spine, dot, time, main);
    return item;
  }

  // Elimina el bloque dummy "—" si existiera
  function removeEmptyDay() {
    const day = feed.querySelector(".day");
    if (!day) return;
    const title = day.querySelector(".day-title");
    if (title && title.textContent.trim() === "—") day.remove();
  }

  // Inserta nueva fila (arriba) y crea cabecera de día si hace falta
  function prependEvent({ status, atIso }) {
    removeEmptyDay();

    const meta = statusMap[status] || statusMap.pending;
    const whenDate = atIso ? new Date(atIso) : new Date();

    // Quitar "is-current" del que estuviera marcado
    const prevCurrent = feed.querySelector(".item.is-current");
    if (prevCurrent) prevCurrent.classList.remove("is-current");

    // Crear / localizar grupo del día
    const newDayText = dayTitle(whenDate);
    let dayGroup = feed.querySelector(".day");
    const currentTitle = dayGroup?.querySelector(".day-title")?.textContent?.trim().toLowerCase();

    if (!dayGroup || (currentTitle !== newDayText.toLowerCase())) {
      dayGroup = document.createElement("div");
      dayGroup.className = "day";
      const title = document.createElement("div");
      title.className = "day-title";
      title.textContent = newDayText;
      dayGroup.appendChild(title);
      feed.prepend(dayGroup);
    }

    // Preprender ítem
    const item = buildItem({
      kind: meta.kind, title: meta.title, sub: meta.sub, whenDate, isCurrent: true
    });
    const firstItem = dayGroup.querySelector(".item");
    if (firstItem) dayGroup.insertBefore(item, firstItem);
    else dayGroup.appendChild(item);

    // Refrescar banner “en vivo”
    if (liveTitle) liveTitle.textContent = meta.title;
    if (liveSub)   liveSub.textContent   = meta.sub || "";
    if (liveTime)  liveTime.textContent  = fmtTime.format(whenDate);
  }

  // ========= Poll =========
  async function poll() {
    try {
      const r = await fetch(pollUrl, { cache: "no-store" });
      if (!r.ok) return;
      const data = await r.json();
      if (!data.ok) return;

      const status = data.status;
      const count  = parseInt(data.events_count || 0, 10);
      const ev     = data.last_event || null;

      // 1) Sincroniza TAG y STEPPER siempre que cambie
      if (status !== lastStatus) {
        updateStatusTag(status);
        updateStepper(status);
      }

      // 2) Actualiza banner actual si no vino evento
      if (status !== lastStatus && !ev) {
        const m = statusMap[status] || statusMap.pending;
        if (liveTitle) liveTitle.textContent = m.title;
        if (liveSub)   liveSub.textContent   = m.sub || "";
        const currentRow = feed.querySelector(".item.is-current");
        if (currentRow) applyKind(currentRow, m.kind);
      }

      // 3) Si hay evento nuevo o cambió el conteo, preprende SIN recargar
      if (count !== lastCount || (ev && ev.created_at && ev.created_at !== lastEventIso)) {
        const atIso = ev && ev.created_at ? ev.created_at : null;
        prependEvent({ status, atIso });
        lastCount    = count;
        lastEventIso = atIso;
      }

      lastStatus = status;
    } catch (e) {
      // silencioso
    }
  }

  // Kickstart: al cargar, alinea stepper/tag con el estado actual del server
  updateStatusTag(lastStatus);
  updateStepper(lastStatus);

  // 4s = equilibrio
  setInterval(poll, 4000);
})();
