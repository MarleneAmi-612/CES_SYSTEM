from django.shortcuts import render, redirect
from django.utils import timezone
import unicodedata
from django.http import JsonResponse
from .models_ces import Alumnos as AlumnoSim  # BD simulada CES (alias 'ces')
from .models import Program, Request, RequestEvent
from .forms import EmailForm, BasicDataForm, ExtrasCPROEMForm, ExtrasDC3Form
from administracion.models import Graduate, CertificateType, Template
from django.views.decorators.http import require_GET
from django.http import JsonResponse
def _norm_name(s: str) -> str:
    """
    Normaliza nombres/apellidos: trim, minúsculas, sin acentos y con espacios colapsados.
    'José   Luis' -> 'jose luis'
    """
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # quita acentos
    return " ".join(s.split())


def _route_for_program(program):
    """
    Devuelve la URL name según el tipo de constancia del programa.
    Evita usar IDs mágicos; usa el nombre del CertificateType.
    """
    ct = getattr(program, "certificate_type", None)
    if not ct or not getattr(ct, "name", None):
        return "alumnos:confirm"  # fallback seguro

    name = ct.name.strip().lower()
    if "cproem" in name:
        return "alumnos:extras_cproem"
    if "dc3" in name:
        return "alumnos:extras_dc3"
    return "alumnos:confirm"


def start(request):
    """
    Paso 0: Verificación por correo en la BD ces (simulación).
    Si existe, guarda el correo en sesión. NO hace prefill de nombre/apellido.

    Además: si venimos de 'Reenviar solicitud', guardamos el ID original en sesión.
    """
    # ← NUEVO: guardar origen de reenvío si llega ?resubmit=<id>
    resubmit_id = request.GET.get("resubmit")
    if resubmit_id:
        try:
            request.session["resub_from"] = int(resubmit_id)
        except (TypeError, ValueError):
            request.session.pop("resub_from", None)

    if request.method == "POST":
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            # Consulta contra la BD de simulación usando el alias 'ces'
            exists = AlumnoSim.objects.using("ces").filter(correo=email).exists()
            if not exists:
                return render(
                    request,
                    "alumnos/email.html",
                    {"form": form, "error": "No encontramos tu correo. Verifícalo."}
                )

            # Guardar en sesión SOLO el correo (sin prefill)
            request.session["alumno_email"] = email
            return redirect("alumnos:basic")
    else:
        form = EmailForm()

    return render(request, "alumnos/email.html", {"form": form})


def basic(request):
    """
    Paso 1: Usuario captura nombre/apellidos y elige programa.
    Se valida que nombre y apellidos coincidan con lo registrado en CES para ese correo.
    """
    if "alumno_email" not in request.session:
        return redirect("alumnos:start")

    email = request.session["alumno_email"]
    alumno_db = AlumnoSim.objects.using("ces").filter(correo=email).first()

    missing_fields = []

    if request.method == "POST":
        form = BasicDataForm(request.POST)
        if form.is_valid():
            # ---- Validación de coincidencia con BD (si la tabla trae nombre/apellido) ----
            db_nombre = getattr(alumno_db, "nombre", None)
            db_apellido = getattr(alumno_db, "apellido", None)

            if db_nombre is not None and db_apellido is not None:
                input_nombre = form.cleaned_data["name"]
                input_apellido = form.cleaned_data["lastname"]

                if _norm_name(input_nombre) != _norm_name(db_nombre):
                    form.add_error("name", "El nombre no coincide con el registrado en CES.")
                if _norm_name(input_apellido) != _norm_name(db_apellido):
                    form.add_error("lastname", "Los apellidos no coinciden con los registrados en CES.")

            if form.errors:
                # Consolidar errores para la alerta superior
                for field, errors in form.errors.items():
                    label = form.fields[field].label
                    for e in errors:
                        missing_fields.append(f"{label}: {e}")
                return render(request, "alumnos/basic.html", {"form": form, "missing_fields": missing_fields})

            # Guardar datos correctos y continuar el flujo
            program = form.cleaned_data["program"]
            request.session["basic"] = {
                "name": form.cleaned_data["name"].strip(),
                "lastname": form.cleaned_data["lastname"].strip(),
                "program_id": program.id,
            }

            # 👉 Decidir a qué vista ir según el tipo de constancia
            next_view = _route_for_program(program)
            return redirect(next_view)

        else:
            # Juntar todos los errores en una lista legible
            for field, errors in form.errors.items():
                label = form.fields[field].label
                for e in errors:
                    missing_fields.append(f"{label}: {e}")
    else:
        # Campos vacíos (sin prefill)
        form = BasicDataForm()

    return render(request, "alumnos/basic.html", {
        "form": form,
        "missing_fields": missing_fields
    })


def extras_cproem(request):
    """
    Paso 2A: Datos extra para CPROEM (solo CURP).
    """
    if "alumno_email" not in request.session or "basic" not in request.session:
        return redirect("alumnos:start")

    if request.method == "POST":
        form = ExtrasCPROEMForm(request.POST)
        if form.is_valid():
            request.session["extras"] = form.cleaned_data
            return redirect("alumnos:confirm")
    else:
        form = ExtrasCPROEMForm()

    return render(request, "alumnos/extras_cproem.html", {"form": form})


def extras_dc3(request):
    """
    Paso 2B: Datos extra para DC3 (CURP, RFC, Puesto, Giro, Razón social).
    """
    if "alumno_email" not in request.session or "basic" not in request.session:
        return redirect("alumnos:start")

    if request.method == "POST":
        form = ExtrasDC3Form(request.POST)
        if form.is_valid():
            request.session["extras"] = form.cleaned_data
            return redirect("alumnos:confirm")
    else:
        form = ExtrasDC3Form()

    return render(request, "alumnos/extras_dc3.html", {"form": form})


def confirm(request):
    """
    Paso 3: Confirmación y envío.
    Doble verificación (opcional) de nombre/apellidos contra BD antes de crear la solicitud.
    Si el usuario viene de 'Reenviar solicitud', al crear la nueva, registramos un RequestEvent('resubmitted').
    """
    if "alumno_email" not in request.session or "basic" not in request.session:
        return redirect("alumnos:start")

    email = request.session["alumno_email"]
    basic = request.session.get("basic", {})
    extras = request.session.get("extras", {})

    if request.method == "POST":
        # Doble chequeo por seguridad (por si alguien manipula la petición)
        alumno_db = AlumnoSim.objects.using("ces").filter(correo=email).first()
        if alumno_db and hasattr(alumno_db, "nombre") and hasattr(alumno_db, "apellido"):
            if _norm_name(basic["name"]) != _norm_name(alumno_db.nombre) or \
               _norm_name(basic["lastname"]) != _norm_name(alumno_db.apellido):
                program = Program.objects.get(id=basic["program_id"])
                has_extras = any([
                    extras.get("curp"),
                    extras.get("rfc"),
                    extras.get("job_title"),
                    extras.get("industry"),
                    extras.get("business_name"),
                ])
                return render(request, "alumnos/confirm.html", {
                    "email": email, "basic": basic, "extras": extras,
                    "program": program, "has_extras": has_extras,
                    "error": "Los datos no coinciden con el registro de CES. Verifícalos.",
                })

        # Crear la NUEVA solicitud
        new_req = Request.objects.create(
            name=basic["name"],
            lastname=basic["lastname"],
            email=email,
            curp=extras.get("curp"),
            rfc=extras.get("rfc"),
            job_title=extras.get("job_title"),
            industry=extras.get("industry"),
            business_name=extras.get("business_name"),
            status="pending",
            sent_at=timezone.now(),
            program_id=basic["program_id"],
        )

        # ← NUEVO: si venimos de un reenvío, registrar evento en la NUEVA solicitud
        old_id = request.session.pop("resub_from", None)
    if old_id:
        try:
        # Evento visible en el historial de la nueva solicitud
            RequestEvent.objects.create(request=new_req, status="resubmitted")
        except Exception:
            pass
    # (Opcional) anota también en la vieja solicitud
    try:
        RequestEvent.objects.create(request_id=old_id, status="resubmitted_from")
    except Exception:
        pass

        # Limpiar sesión
        for k in ("alumno_email", "basic", "extras"):
            request.session.pop(k, None)

        return render(request, "alumnos/success.html")

    # GET: vista previa
    program = Program.objects.get(id=basic["program_id"])
    has_extras = any([
        extras.get("curp"),
        extras.get("rfc"),
        extras.get("job_title"),
        extras.get("industry"),
        extras.get("business_name"),
    ])
    ctx = {
        "email": email,
        "basic": basic,
        "extras": extras,
        "program": program,
        "has_extras": has_extras,
    }
    return render(request, "alumnos/confirm.html", ctx)

def status(request):
    """
    Página de búsqueda por correo. Si hay 1 solicitud, redirige a tracking.
    Si hay varias, muestra lista para elegir.
    """
    ctx = {"results": None, "error": None, "email_query": ""}

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        ctx["email_query"] = email
        if not email:
            ctx["error"] = "Ingresa un correo para buscar."
            return render(request, "alumnos/status.html", ctx)

        qs = Request.objects.filter(email__iexact=email).order_by("-sent_at")
        if not qs.exists():
            ctx["results"] = []
            return render(request, "alumnos/status.html", ctx)

        if qs.count() == 1:
            req = qs.first()
            # Pase temporal de seguimiento por 15 min
            request.session["tracking_ok"] = True
            request.session["tracking_issued_at"] = timezone.now().isoformat()
            request.session["status_email"] = email  # útil si quieres mostrarlo

            return redirect("alumnos:tracking", request_id=req.id)

        # Varias solicitudes: lista para elegir (y al elegir, aplicar el mismo pase)
        ctx["results"] = qs
        return render(request, "alumnos/status.html", ctx)

    # GET
    return render(request, "alumnos/status.html", ctx)

def _status_rank(status: str) -> int:
    order = {
        "pending": 1,
        "review": 2,
        "accepted": 3,
        "rejected": 3,       # estado terminal en el paso 3
        "generating": 4,
        "generated": 4,
        "emailed": 5,
        "downloaded": 6,
    }
    return order.get(status, 1)

def _build_tracking_steps(req: Request):
    """
    Construye los pasos para el stepper + info de graduado si aplica.
    Corrige la "completitud" de pasos usando una jerarquía de estados
    para que 'generating' marque como hechos 1..3, etc.
    """
    grad = getattr(req, "graduate", None)

    sent_at = req.sent_at
    approved_at = getattr(grad, "completion_date", None) if grad else None
    generated_at = getattr(grad, "completion_date", None) if (grad and grad.diploma_file) else None
    mailed_at = getattr(grad, "sent_at", None) if grad else None
    downloaded_at = getattr(grad, "download_date", None) if grad else None

    rank = _status_rank(req.status)

    steps = [
        {"key": "sent",       "title": "Solicitud enviada",                 "timestamp": sent_at,       "done": rank >= 1},
        {"key": "review",     "title": "En revisión",                       "timestamp": sent_at,       "done": rank >= 2},
        {"key": "accepted",   "title": "Aprobada",                          "timestamp": approved_at,   "done": rank >= 3},
        {"key": "generated",  "title": "Diploma/Constancia generada",       "timestamp": generated_at,  "done": req.status in ("generated", "emailed", "downloaded") or bool(generated_at)},
        {"key": "emailed",    "title": "Enviado por correo",                "timestamp": mailed_at,     "done": req.status in ("emailed", "downloaded") or bool(mailed_at)},
        {"key": "downloaded", "title": "Descargado por el alumno",          "timestamp": downloaded_at, "done": req.status == "downloaded" or bool(downloaded_at)},
    ]

    # Si está rechazado, el paso 3 cambia de nombre y se considera alcanzado (terminal)
    if req.status == "rejected":
        steps[2]["title"] = "Solicitud rechazada"
        steps[2]["done"] = True

    # Índice visible/actual para resaltar en naranja (1..6)
    active_index_map = {
        "pending": 1, "review": 2, "accepted": 3, "rejected": 3,
        "generating": 4, "generated": 4, "emailed": 5, "downloaded": 6,
    }
    active_index = active_index_map.get(req.status, 1)

    # Campos de apoyo para el historial
    for s in steps:
        s["display"] = s["title"]
        k = s["key"]
        if k == "rejected":
            s["tone"] = "bad"
        elif k in ("sent", "accepted", "downloaded"):
            s["tone"] = "good"
        else:
            s["tone"] = "info"

    return steps, active_index, grad



def _build_tracking_steps(req: Request):
    """
    Construye los pasos para el stepper + info de graduado si aplica.
    Corrige la "completitud" de pasos usando una jerarquía de estados
    para que 'generating' marque como hechos 1..3, etc.
    """
    grad = getattr(req, "graduate", None)

    sent_at = req.sent_at
    approved_at = getattr(grad, "completion_date", None) if grad else None
    generated_at = getattr(grad, "completion_date", None) if (grad and grad.diploma_file) else None
    mailed_at = getattr(grad, "sent_at", None) if grad else None
    downloaded_at = getattr(grad, "download_date", None) if grad else None

    rank = _status_rank(req.status)

    steps = [
        {"key": "sent",       "title": "Solicitud enviada",                 "timestamp": sent_at,       "done": rank >= 1},
        {"key": "review",     "title": "En revisión",                       "timestamp": sent_at,       "done": rank >= 2},
        {"key": "accepted",   "title": "Aprobada",                          "timestamp": approved_at,   "done": rank >= 3},
        {"key": "generated",  "title": "Diploma/Constancia generada",       "timestamp": generated_at,  "done": req.status in ("generated", "emailed", "downloaded") or bool(generated_at)},
        {"key": "emailed",    "title": "Enviado por correo",                "timestamp": mailed_at,     "done": req.status in ("emailed", "downloaded") or bool(mailed_at)},
        {"key": "downloaded", "title": "Descargado por el alumno",          "timestamp": downloaded_at, "done": req.status == "downloaded" or bool(downloaded_at)},
    ]

    # Si está rechazado, el paso 3 cambia de nombre y se considera alcanzado (terminal)
    if req.status == "rejected":
        steps[2]["title"] = "Solicitud rechazada"
        steps[2]["done"] = True

    # Índice visible/actual para resaltar en naranja (1..6)
    active_index_map = {
        "pending": 1, "review": 2, "accepted": 3, "rejected": 3,
        "generating": 4, "generated": 4, "emailed": 5, "downloaded": 6,
    }
    active_index = active_index_map.get(req.status, 1)

    # Campos de apoyo para el historial
    for s in steps:
        s["display"] = s["title"]
        k = s["key"]
        if k == "rejected":
            s["tone"] = "bad"
        elif k in ("sent", "accepted", "downloaded"):
            s["tone"] = "good"
        else:
            s["tone"] = "info"

    return steps, active_index, grad

@require_GET
def tracking_api(request, request_id):
    req = Request.objects.filter(id=request_id).first()
    if not req:
        return JsonResponse({"ok": False, "msg": "Not found"}, status=404)

    ev = req.events.order_by("-created_at").first()  # usa tu modelo RequestEvent(status, created_at)
    last_event = None
    if ev:
        last_event = {
            "status": ev.status,                          # p.ej. "accepted", "review", etc.
            "created_at": ev.created_at.isoformat(),      # hora exacta del servidor
        }

    return JsonResponse({
        "ok": True,
        "status": req.status,
        "events_count": req.events.count(),
        "last_event": last_event
    })

def tracking(request, request_id):
    req = Request.objects.filter(id=request_id).first()
    if not req:
        return render(request, "alumnos/tracking.html", {"not_found": True})

    steps, current_index, grad = _build_tracking_steps(req)

    total_steps = len(steps) or 1
    progress_pct = int(((current_index + 1) * 100) // total_steps)

    # Eventos guardados
    events_count = RequestEvent.objects.filter(request=req).count()

    # 🔸 NUEVO: qué paso debe verse “activo” (naranja)
    status_to_active = {
        "pending": 1,
        "review": 2,
        "accepted": 3,
        "generating": 4,     # <- aquí activamos el 4
        "generated": 4,
        "emailed": 5,
        "downloaded": 6,
        "rejected": 3,       # hasta rechazo
    }
    active_max = status_to_active.get(req.status, current_index + 1)

    return render(request, "alumnos/tracking.html", {
        "req": req,
        "steps": steps,
        "current_index": current_index,
        "grad": grad,
        "progress_pct": progress_pct,
        "events_count": events_count,
        "active_max": active_max,   # <- pásalo al template
    })

@require_GET
def tracking_api(request, request_id):
    req = Request.objects.filter(id=request_id).first()
    if not req:
        return JsonResponse({"ok": False, "msg": "Not found"}, status=404)

    events_count = RequestEvent.objects.filter(request=req).count()

    return JsonResponse({
        "ok": True,
        "status": req.status,
        "status_reason": getattr(req, "status_reason", "") or "",
        "events_count": events_count,
    })
def _build_history(req: Request, steps=None):
    """
    Devuelve una lista de eventos estilo 'feed'.
    Acepta 'steps' opcional para construir el historial a partir de los pasos + eventos.
    """
    def label_for(key: str) -> str:
        return {
            "sent": "Solicitud enviada",
            "review": "En revisión",
            "accepted": "Aprobada",
            "rejected": "Solicitud rechazada",
            "generated": "Documento generado",
            "emailed": "Enviado por correo",
            "downloaded": "Descargado por el alumno",
        }.get(key, key.replace("_", " ").title())

    items = []

    # 1) Pasos (si vienen):
    if steps:
        for st in steps:
            ts = st.get("timestamp")
            if not ts:
                continue
            key = st.get("key")
            tone = "bad" if key == "rejected" else ("ok" if key in ("sent", "accepted", "downloaded") else "info")
            items.append({
                "when": ts,
                "title": label_for(key),
                "tone": tone,
                "note": "Actualización registrada.",
            })

    # 2) Eventos extras guardados en RequestEvent (usa 'status', no 'key')
    extra_qs = req.events.filter(status__in=["resubmitted", "resubmitted_from"]).order_by("created_at")
    for ev in extra_qs:
        title = "Solicitud reenviada" if ev.status == "resubmitted" else "Reenvío desde solicitud anterior"
        items.append({
            "when": ev.created_at,
            "title": title,
            "tone": "info",
            "note": (ev.note or "Actualización registrada."),
        })

    # Orden cronológico ascendente (o cambia a reverse=True si la quieres más reciente primero)
    items.sort(key=lambda x: x["when"])
    return items
