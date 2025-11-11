from datetime import timedelta, date
import unicodedata
import datetime
from django.urls import reverse
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET,require_POST
from django.http import JsonResponse
from .models_ces import Alumnos as AlumnoSim  # BD simulada (alias 'ces')
from .models import Program, Request, RequestEvent
from .forms import EmailForm, BasicDataForm, ExtrasCPROEMForm, ExtrasDC3Form

RESUBMIT_DAYS = 10  

def help_view(request):
    return render(request, 'alumnos/help.html')
#Utilidades

def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.split())


def _add_business_days(d: date, days: int) -> date:
    cur = d
    remaining = days
    while remaining > 0:
        cur += timedelta(days=1)
        if cur.weekday() < 5:  # L-V
            remaining -= 1
    return cur



def _route_for_program(program):
    ct = getattr(program, "certificate_type", None)
    if not ct or not getattr(ct, "name", None):
        return "alumnos:confirm"
    name = ct.name.strip().lower()
    if "cproem" in name:
        return "alumnos:extras_cproem"
    if "dc3" in name:
        return "alumnos:extras_dc3"
    return "alumnos:confirm"

def _can_resubmit(req: Request) -> bool:
    """
    Permite reenviar si la solicitud está rechazada y el rechazo
    ocurrió hace no más de RESUBMIT_DAYS días.
    """
    if req.status != "rejected":
        return False

    last_reject = (
        req.events.filter(status="rejected")
        .order_by("-created_at")
        .first()
    )
    base_dt = last_reject.created_at if last_reject else req.sent_at
    if not base_dt:
        return False

    return timezone.now() <= (base_dt + timedelta(days=RESUBMIT_DAYS))
#Flujo de captura 

def start(request):
    """Paso 0: validar correo en la BD simulada y pasar al formulario básico."""
    # Guardar origen si venimos de reenvío
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
            exists = AlumnoSim.objects.using("ces").filter(correo=email).exists()
            if not exists:
                return render(
                    request, "alumnos/email.html",
                    {"form": form, "error": "No encontramos tu correo. Verifícalo."}
                )
            request.session["alumno_email"] = email
            return redirect("alumnos:basic")
    else:
        form = EmailForm()

    return render(request, "alumnos/email.html", {"form": form})


def basic(request):
    """Paso 1: nombre + apellidos + programa. Valida contra simulación si hay nombre/apellido."""
    if "alumno_email" not in request.session:
        return redirect("alumnos:start")

    email = request.session["alumno_email"]
    alumno_db = AlumnoSim.objects.using("ces").filter(correo=email).first()
    missing_fields = []

    if request.method == "POST":
        form = BasicDataForm(request.POST)
        if form.is_valid():
            # Validar contra simulación si hay nombre/apellido
            db_nombre = getattr(alumno_db, "nombre", None)
            db_apellido = getattr(alumno_db, "apellido", None)
            if db_nombre is not None and db_apellido is not None:
                if _norm_name(form.cleaned_data["name"]) != _norm_name(db_nombre):
                    form.add_error("name", "El nombre no coincide con el registrado en CES.")
                if _norm_name(form.cleaned_data["lastname"]) != _norm_name(db_apellido):
                    form.add_error("lastname", "Los apellidos no coinciden con los registrados en CES.")
            if form.errors:
                for field, errors in form.errors.items():
                    label = form.fields[field].label
                    for e in errors:
                        missing_fields.append(f"{label}: {e}")
                return render(request, "alumnos/basic.html", {"form": form, "missing_fields": missing_fields})

            program = form.cleaned_data["program"]
            request.session["basic"] = {
                "name": form.cleaned_data["name"].strip(),
                "lastname": form.cleaned_data["lastname"].strip(),
                "program_id": program.id,
            }
            return redirect(_route_for_program(program))
        else:
            for field, errors in form.errors.items():
                label = form.fields[field].label
                for e in errors:
                    missing_fields.append(f"{label}: {e}")
    else:
        form = BasicDataForm()

    return render(request, "alumnos/basic.html", {"form": form, "missing_fields": missing_fields})


def extras_cproem(request):
    """Paso 2A: extras para CPROEM (CURP)."""
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
    """Paso 2B: extras para DC3 (CURP, RFC, Puesto, Giro, Razón social)."""
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
    """Paso 3: confirmar y crear la solicitud."""
    if "alumno_email" not in request.session or "basic" not in request.session:
        return redirect("alumnos:start")

    email = request.session["alumno_email"]
    basic = request.session.get("basic", {}) or {}
    extras = request.session.get("extras", {}) or {}

    if request.method == "POST":
        # Doble verificación opcional
        alumno_db = AlumnoSim.objects.using("ces").filter(correo=email).first()
        if alumno_db and hasattr(alumno_db, "nombre") and hasattr(alumno_db, "apellido"):
            if _norm_name(basic.get("name", "")) != _norm_name(alumno_db.nombre) or \
               _norm_name(basic.get("lastname", "")) != _norm_name(alumno_db.apellido):
                try:
                    program = Program.objects.get(id=basic.get("program_id"))
                except Program.DoesNotExist:
                    program = None
                has_extras = any(extras.get(k) for k in ("curp", "rfc", "job_title", "industry", "business_name"))
                return render(request, "alumnos/confirm.html", {
                    "email": email, "basic": basic, "extras": extras,
                    "program": program, "has_extras": has_extras,
                    "error": "Los datos no coinciden con el registro de CES. Verifícalos.",
                })

        # Crear solicitud
        new_req = Request.objects.create(
            name=basic.get("name", ""),
            lastname=basic.get("lastname", ""),
            email=email,
            curp=extras.get("curp"),
            rfc=extras.get("rfc"),
            job_title=extras.get("job_title"),
            industry=extras.get("industry"),
            business_name=extras.get("business_name"),
            status="pending",
            sent_at=timezone.now(),
            program_id=basic.get("program_id"),
        )

        # Registrar reenvío si aplica
        old_id = request.session.pop("resub_from", None)
        if old_id:
            try:
                RequestEvent.objects.create(request=new_req, status="resubmitted")
            except Exception:
                pass
            try:
                RequestEvent.objects.create(request_id=old_id, status="resubmitted_from")
            except Exception:
                pass

        # Limpiar sesión
        for k in ("alumno_email", "basic", "extras"):
            request.session.pop(k, None)

        return render(request, "alumnos/success.html")

    #vista previa
    try:
        program = Program.objects.get(id=basic.get("program_id"))
    except Program.DoesNotExist:
        program = None

    has_extras = any(extras.get(k) for k in ("curp", "rfc", "job_title", "industry", "business_name"))

    return render(request, "alumnos/confirm.html", {
        "email": email, "basic": basic, "extras": extras,
        "program": program, "has_extras": has_extras,
    })


def status(request):
    """
    Búsqueda por correo:
      - Si hay 0 → mostrar lista vacía
      - Si hay 1 → redirigir a tracking
      - Si hay >1 → mostrar lista para elegir
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
            # Pase temporal si lo necesitas (opcional)
            request.session["tracking_ok"] = True
            request.session["tracking_issued_at"] = timezone.now().isoformat()
            request.session["status_email"] = email
            return redirect("alumnos:tracking", request_id=req.id)

        ctx["results"] = qs
        return render(request, "alumnos/status.html", ctx)

    return render(request, "alumnos/status.html", ctx)


# Tracking

def _status_rank(status: str) -> int:
    order = {
        "pending": 1, "review": 2, "accepted": 3, "rejected": 3,
        "generating": 4, "generated": 4, "emailed": 5, "downloaded": 6,
    }
    return order.get(status, 1)

def _build_tracking_steps(req: Request):
    grad = getattr(req, "graduate", None)

    sent_at       = req.sent_at
    approved_at   = getattr(grad, "completion_date", None) if grad else None
    generated_at  = getattr(grad, "completion_date", None) if (grad and getattr(grad, "diploma_file", None)) else None
    mailed_at     = getattr(grad, "sent_at", None) if grad else None
    downloaded_at = getattr(grad, "download_date", None) if grad else None

    rank = _status_rank(req.status or "")

    steps = [
        {"key": "sent",       "title": "Solicitud enviada",            "timestamp": sent_at,       "done": rank >= 1},
        {"key": "review",     "title": "En revisión",                  "timestamp": sent_at,       "done": rank >= 2},
        {"key": "accepted",   "title": "Aprobada",                     "timestamp": approved_at,   "done": rank >= 3},
        {"key": "generated",  "title": "Diploma/Constancia generada",  "timestamp": generated_at,
         "done": req.status in ("generated", "emailed", "downloaded", "finalizado") or bool(generated_at)},
        {"key": "emailed",    "title": "Enviado por correo",           "timestamp": mailed_at,
         "done": req.status in ("emailed", "downloaded", "finalizado") or bool(mailed_at)},
        {"key": "downloaded", "title": "Descargado por el alumno",     "timestamp": downloaded_at,
         "done": req.status in ("downloaded", "finalizado") or bool(downloaded_at)},
    ]

    if req.status == "rejected":
        steps[2]["title"] = "Solicitud rechazada"
        steps[2]["done"] = True

    active_index_map = {
        "pending": 2,
        "review": 2,
        "accepted": 3,
        "rejected": 3,
        "generating": 4,
        "generated": 4,
        "emailed": 5,
        "downloaded": 6,
        "finalizado": 6,  # 👈 círculo 6
    }
    active_index = active_index_map.get(req.status, 1)

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



def _build_history(req: Request, steps=None):
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

    extra_qs = req.events.filter(status__in=["resubmitted", "resubmitted_from"]).order_by("created_at")
    for ev in extra_qs:
        title = "Solicitud reenviada" if ev.status == "resubmitted" else "Reenvío desde solicitud anterior"
        items.append({
            "when": ev.created_at,
            "title": title,
            "tone": "info",
            "note": (ev.note or "Actualización registrada."),
        })

    items.sort(key=lambda x: x["when"])
    return items

@require_GET
def tracking(request, request_id):
    req = Request.objects.filter(id=request_id).first()
    if not req:
        return render(request, "alumnos/tracking.html", {"not_found": True})

    # Construye pasos
    steps, _current_index, grad = _build_tracking_steps(req)

    # === Círculo activo (naranja) ===
    status = (req.status or "").lower()
    status_to_step = {
        "pending":    1,  # Solicitud enviada
        "review":     2,  # En revisión
        "accepted":   3,  # Aprobada
        "rejected":   3,  # Rechazada
        "generating": 4,  # Generando
        "generated":  4,  # Generado
        "emailed":    5,  # Enviado por correo
        "downloaded": 6,  # Descargado
        "finalizado": 6,  # Finalizado (Círculo 6)
    }
    active_max = status_to_step.get(status, 1)

    # === Línea de progreso con medios pasos ===
    TOTAL_STEPS = 6
    total_segments = TOTAL_STEPS - 1  # 5 tramos

    if status in ("downloaded", "finalizado"):
        # Llega al 100%
        units = total_segments
    elif status == "rejected":
        # Se queda justo en el 3 (sin 0.5 extra)
        units = (active_max - 1)
    else:
        # Avanza medio tramo hacia el siguiente
        units = (active_max - 1) + 0.5

    progress_pct = int(round((units / total_segments) * 100))

    # Eventos para el contador en el feed
    events_count = RequestEvent.objects.filter(request=req).count()

    # ETA (10 días hábiles desde la fecha de envío)
    sent_local = timezone.localtime(req.sent_at).date() if req.sent_at else timezone.localdate()
    eta_date = _add_business_days(sent_local, 10)

    # Motivo de rechazo (si aplica)
    rejection_reason = getattr(req, "status_reason", "") or ""

    # Historial (incluye pasos con timestamp y eventos adicionales)
    history = _build_history(req, steps)

    # ¿Se puede reenviar?
    can_resubmit = _can_resubmit(req)

    # === Descarga CPROEM para el alumno ===
    program   = getattr(req, "program", None)
    cert_type = getattr(program, "certificate_type", None)
    cert_name = (getattr(cert_type, "name", "") or "").strip().lower()
    is_cproem = "cproem" in cert_name

    can_download_cproem = is_cproem and status in ("finalizado", "downloaded")
    cproem_download_url = None
    if can_download_cproem:
        cproem_download_url = (
            reverse("administracion:doc_download", args=[req.id])
            + "?tipo=constancia&fmt=pdf"
        )

    return render(request, "alumnos/tracking.html", {
        "req": req,
        "steps": steps,
        "current_index": active_max - 1,
        "grad": grad,
        "progress_pct": progress_pct,
        "events_count": events_count,
        "active_max": active_max,
        "eta_date": eta_date,
        "rejection_reason": rejection_reason,
        "history": history,
        "can_resubmit": can_resubmit,
        "can_download_cproem": can_download_cproem,
        "cproem_download_url": cproem_download_url,
    })


@require_GET
def tracking_api(request, request_id):
    req = Request.objects.filter(id=request_id).first()
    if not req:
        return JsonResponse({"ok": False, "msg": "Not found"}, status=404)

    ev = req.events.order_by("-created_at").first()
    last_event = None
    if ev:
        last_event = {"status": ev.status, "created_at": ev.created_at.isoformat()}

    return JsonResponse({
        "ok": True,
        "status": req.status,
        "status_reason": getattr(req, "status_reason", "") or "",
        "events_count": req.events.count(),
        "last_event": last_event,
    })

def _can_resubmit(req) -> bool:
    """
    Regla de negocio para permitir reenvío.
    Aquí: si está 'rejected' y el rechazo fue dentro de los últimos 30 días.
    Puedes ajustar días o lógica según tu necesidad.
    """
    if req.status != "rejected":
        return False
    # Tomamos como referencia la última fecha de evento 'rejected' o el sent_at.
    last_rej = (
        req.events.filter(status="rejected")
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    base_dt = last_rej or req.sent_at or timezone.now()
    return (timezone.now() - base_dt) <= timedelta(days=30)

@require_POST
def resubmit(request, request_id):
    """
    Reenvía la solicitud (solo si está 'rejected' y dentro de la ventana permitida).
    - Cambia status -> 'pending'
    - Limpia 'status_reason'
    - Actualiza 'sent_at' a ahora (sube en listados)
    - Registra RequestEvent('resubmitted')
    """
    req = get_object_or_404(Request, id=request_id)

    if req.status != "rejected" or not _can_resubmit(req):
        # No permitido: vuelve a tracking sin cambios
        return redirect("alumnos:tracking", request_id=request_id)

    req.status = "pending"
    req.status_reason = ""
    req.sent_at = timezone.now()
    req.save(update_fields=["status", "status_reason", "sent_at"])

    RequestEvent.objects.create(
        request=req,
        status="resubmitted",
        note="Alumno reenvi\u00f3 la solicitud desde tracking."
    )

    return redirect("alumnos:tracking", request_id=request_id)

@require_POST
def resubmit(request, request_id: int):
    """
    Reenvía una solicitud RECHAZADA:
      - cambia estado a 'pending'
      - limpia el motivo
      - actualiza 'sent_at'
      - registra eventos
      - redirige a 'next' (si viene) o de regreso al tracking con ?resubmitted=1
    """
    req = get_object_or_404(Request, pk=request_id)

    # Seguridad suave: solo permitir si estaba rechazada
    if req.status != "rejected":
        # Si no está rechazada, simplemente regresar al tracking sin cambios
        next_url = request.POST.get("next") or reverse("alumnos:tracking", args=[req.id])
        return redirect(next_url)

    # Cambiar a pendiente y “re-fechar” la solicitud
    req.status = "pending"
    req.status_reason = ""
    req.sent_at = timezone.now()
    req.save(update_fields=["status", "status_reason", "sent_at"])

    # Eventos (para el feed / auditoría)
    try:
        RequestEvent.objects.create(request=req, status="resubmitted", note="Alumno reenvi&oacute; la solicitud.")
    except Exception:
        pass

    # reflejar el nuevo estado como evento explícito
    if not RequestEvent.objects.filter(request=req, status="pending").exists():
        RequestEvent.objects.create(request=req, status="pending", note="Solicitud puesta en pendiente tras reenv&iacute;o.")

    # Redirección con bandera para mostrar el banner y el meta-refresh
    next_url = request.POST.get("next")
    if not next_url:
        next_url = reverse("alumnos:tracking", args=[req.id]) + "?resubmitted=1"
    return redirect(next_url)

@require_POST
def tracking_resend(request, request_id:int):
    """Pasa una solicitud rechazada a 'pending' y registra evento."""
    req = get_object_or_404(Request, pk=request_id)

    # Sólo permitimos reenviar si estaba rechazada
    if req.status != "rejected":
        return JsonResponse({"ok": False, "msg": "La solicitud no está rechazada."}, status=400)

    # Limpia motivo y vuelve a pendiente
    req.status = "pending"
    req.status_reason = ""
    req.sent_at = req.sent_at or timezone.now()  # conservamos fecha original si no existe
    req.save(update_fields=["status", "status_reason", "sent_at"])

    # Evento
    RequestEvent.objects.create(request=req, status="pending", note="Reenvío de solicitud por el alumno")

    return JsonResponse({"ok": True, "new_status": "pending"})

