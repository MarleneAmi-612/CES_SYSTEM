(function () {
  const feed = document.getElementById("historyFeed");
  const root = document.getElementById("trackingRoot");
  if (!feed || !root) return;

  const pollUrl = root.dataset.pollUrl;
  if (!pollUrl) return;

  // ====== Mapa de estados (texto, subtítulo, color y posición en stepper) ======
const statusMap = {
  pending:    { title: "Solicitud enviada",            sub: "Estamos procesando tu solicitud.",                 kind: "ok",   pos: 1 },
  review:     { title: "Tu solicitud está en revisión.", sub: "Te avisaremos por correo cuando sea aprobada.", kind: "info", pos: 2 },
  accepted:   { title: "¡Aprobada!",                   sub: "Estamos preparando tu documento.",               kind: "ok",   pos: 3 },
  generating: { title: "Generando documento…",         sub: "Puede tardar unos dias.",                        kind: "info", pos: 4 },
  emailed:    { title: "Documento enviado por correo.", sub: "Revisa tu bandeja de entrada.",                 kind: "info", pos: 5 },
  downloaded: { title: "Documento descargado.",        sub: "¡Listo! Guarda tu archivo.",                     kind: "ok",   pos: 6 },
  rejected:   { title: "Solicitud rechazada",          sub: "Se registró un rechazo.",                         kind: "bad",  pos: 3 },
  finalizado: { title: "Documento finalizado.",        sub: "Tu constancia CPROEM está lista para descargar.", kind: "ok",   pos: 6 },
};


  // ====== DOM refs ======
  const liveTitle = document.getElementById("liveTitle");
  const liveSub   = document.getElementById("liveSub");
  const liveTime  = document.getElementById("liveTime");
  const statusTag = document.getElementById("statusTag");
  const progress  = document.getElementById("progressLine");
  const stepEls   = Array.from(document.querySelectorAll(".stepper .step"));

  // ====== Estado previo para evitar duplicados ======
  let lastStatus   = feed.dataset.currentStatus || "";
  let lastCount    = parseInt(feed.dataset.events || "0", 10);
  let lastEventIso = null;

  // ====== Formateadores ======
  const fmtDay  = new Intl.DateTimeFormat("es-MX", { weekday:"long", day:"2-digit", month:"long", year:"numeric" });
  const fmtTime = new Intl.DateTimeFormat("es-MX", { hour:"2-digit", minute:"2-digit", hour12:false });
  const dayTitle = d => fmtDay.format(d);

  // ====== TAG de estado ======
  function updateStatusTag(status) {
    if (!statusTag) return;
    statusTag.className = "tag " + status;
        const text =
      status === "pending"    ? "Pendiente" :
      status === "review"     ? "Revisión" :
      status === "accepted"   ? "Aprobada" :
      status === "generating" ? "Generando" :
      status === "emailed"    ? "Enviada por correo" :
      status === "downloaded" ? "Descargada" :
      status === "finalizado" ? "Finalizado" :
      status === "rejected"   ? "Rechazada" : (status || "");
    statusTag.textContent = text;
  }

  // ====== Stepper con medios pasos ======
  function updateStepper(status) {
    const meta     = statusMap[status] || statusMap.pending;
    const total    = stepEls.length;             // 6 puntos
    const pos      = meta.pos;                   // 1..6 (o 3 para rejected)
    const segments = Math.max(1, total - 1);     // 5 tramos

    // Restaurar clases y labels
    stepEls.forEach((step) => {
      step.classList.remove("done", "current", "bad");
      const label = step.querySelector(".label");
      if (label && label.dataset.title) label.textContent = label.dataset.title;
    });

    // Pinta círculos
    if (status === "rejected") {
      stepEls.forEach((s, i) => { if (i <= 2) s.classList.add("bad", "current", "done"); });
      const step3Label = stepEls[2]?.querySelector(".label");
      if (step3Label) step3Label.textContent = "Solicitud rechazada";
    } else {
      stepEls.forEach((s, i) => { if (i < pos) s.classList.add("done", "current"); });
    }

    // Progreso (medios pasos salvo rechazado/descargado)
    let units;
    if (status === "downloaded") {
      units = segments;           // 100%
    } else if (status === "rejected") {
      units = (pos - 1);          // se queda justo en 3
    } else {
      units = (pos - 1) + 0.5;    // medio tramo hacia el siguiente
    }
    const pct = Math.max(0, Math.min(100, (units / segments) * 100));
    if (progress) progress.style.width = pct.toFixed(0) + "%";
  }

  // ====== Historial ======
  function applyKind(row, kind) {
    row.classList.remove("ok", "bad", "info");
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

  function removeEmptyDay() {
    const day = feed.querySelector(".day");
    if (!day) return;
    const title = day.querySelector(".day-title");
    if (title && title.textContent.trim() === "—") day.remove();
  }

  // Preprende SOLO eventos reales; dedup por (día, hora, título)
  function prependEvent({ status, atIso }) {
    removeEmptyDay();
    const meta = statusMap[status] || statusMap.pending;
    if (!atIso) return; // no insertes si no hay fecha real

    const whenDate = new Date(atIso);

    // quitar current
    const prevCurrent = feed.querySelector(".item.is-current");
    if (prevCurrent) prevCurrent.classList.remove("is-current");

    // agrupar por día estable YYYY-MM-DD
    const dayKey = whenDate.toISOString().slice(0, 10);
    let dayGroup = feed.querySelector(`.day[data-day-key="${dayKey}"]`);
    if (!dayGroup) {
      dayGroup = document.createElement("div");
      dayGroup.className = "day";
      dayGroup.setAttribute("data-day-key", dayKey);

      const title = document.createElement("div");
      title.className = "day-title";
      title.textContent = dayTitle(whenDate);
      dayGroup.appendChild(title);
      feed.prepend(dayGroup);
    }

    // dedup (misma hora + mismo título)
    const timeStr = fmtTime.format(whenDate);
    const exists = Array.from(dayGroup.querySelectorAll(".item")).some(row => {
      const t = row.querySelector(".it-time")?.textContent?.trim();
      const ttl = row.querySelector(".it-title")?.textContent?.trim();
      return t === timeStr && ttl === meta.title;
    });
    if (exists) return;

    // insertar arriba
    const item = buildItem({
      kind: meta.kind, title: meta.title, sub: meta.sub, whenDate, isCurrent: true
    });
    const firstItem = dayGroup.querySelector(".item");
    if (firstItem) dayGroup.insertBefore(item, firstItem);
    else dayGroup.appendChild(item);

    // banner en vivo
    if (liveTitle) liveTitle.textContent = meta.title;
    if (liveSub)   liveSub.textContent   = meta.sub || "";
    if (liveTime)  liveTime.textContent  = timeStr;
  }

  // ====== Polling ======
  async function poll() {
    try {
      const r = await fetch(pollUrl, { cache: "no-store" });
      if (!r.ok) return;
      const data = await r.json();
      if (!data.ok) return;

      const status = data.status;
      const count  = parseInt(data.events_count || 0, 10);
      const ev     = data.last_event || null;

      // Sincroniza TAG y STEPPER si cambia estado
      if (status !== lastStatus) {
        updateStatusTag(status);
        updateStepper(status);

        // Actualiza el banner actual (sin insertar ítem)
        const m = statusMap[status] || statusMap.pending;
        if (liveTitle) liveTitle.textContent = m.title;
        if (liveSub)   liveSub.textContent   = m.sub || "";
        const currentRow = feed.querySelector(".item.is-current");
        if (currentRow) applyKind(currentRow, m.kind);
      }

      // Inserta SOLO si hay evento real y es nuevo
      if (ev && ev.created_at && ev.created_at !== lastEventIso) {
        prependEvent({ status, atIso: ev.created_at });
        lastEventIso = ev.created_at;
        lastCount    = count;
      }

      lastStatus = status;
    } catch (e) {
      // silencioso
    }
  }

  // Kickstart
  updateStatusTag(lastStatus);
  updateStepper(lastStatus);

  // 4s equilibrio
  setInterval(poll, 4000);
})();
