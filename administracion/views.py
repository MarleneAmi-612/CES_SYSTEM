import os
import uuid
import fitz  
import unicodedata
import logging
from datetime import timedelta
import io
from pathlib import Path
import secrets
import requests
import qrcode
import zipfile
import json
import pikepdf
import inspect
import tempfile, subprocess
from django.core.paginator import Paginator
from typing import Optional
from weasyprint import HTML
from django.db import connections, transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .thumbs import save_thumb
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate, login, logout, get_user_model, update_session_auth_hash
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.conf import settings
from django.apps import apps
from django.forms import modelform_factory
from django.utils.html import escape
from django.db.models import Q, Count, Max
from django.http import JsonResponse, HttpResponse, FileResponse, Http404, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.generic import TemplateView, FormView
from django.middleware.csrf import get_token
from django_otp.decorators import otp_required
from base64 import b64encode

# Opcionales para rasterización dentro de _pdf_secure
from PIL import Image  # Pillow
from csp.decorators import csp_update
from csp import constants as csp

# Importa Request/Program del módulo de alumnos
from alumnos.models import Request, Program as ProgramSim, RequestEvent
from django.views.decorators.csrf import csrf_protect

# Modelos del panel
from .models import (
    Graduate, AdminAccessLog, DocToken,
    DesignTemplate, DesignTemplateVersion, TemplateAsset,
    Program as ProgramAdmin,
    ConstanciaType
)
from .forms import AdminLoginForm
from .security import failed_attempts_count
from .models import Program
User = get_user_model()
# Si estás en Windows y quieres rasterizar con pdf2image + Poppler,
POPPLER_BIN = os.environ.get("POPPLER_BIN")
SOFFICE_BIN = os.environ.get("SOFFICE_BIN")  
try:
    from .models import Egresado  # ajusta si tu modelo real tiene otro nombre
except Exception:
    Egresado = None
    
try:
    from .models import Program as ProgramAdmin, ConstanciaType
except ImportError:
    ProgramAdmin, ConstanciaType = None, None

log = logging.getLogger(__name__)

# Campos que permitimos actualizar desde el form/JS
ALLOWED_EGRESADO_FIELDS = [
    "nombre", "apellido_paterno", "apellido_materno",
    "curp", "rfc", "nss", "telefono", "email",
    "status", "notas",
]
# ====================== Endpoint well-known (Chrome DevTools) ======================
@require_GET
def wellknown_devtools(request):
    """
    Atiende /.well-known/appspecific/com.chrome.devtools.json
    Devolver un JSON mínimo es suficiente para que no falle el import en urls.py.
    """
    return JsonResponse({
        "name": "CES System DevTools",
        "status": "ok"
    })

# ====================== Helpers de autorización ======================

def _in_admin_group(user) -> bool:
    try:
        return user.groups.filter(name="AdministradoresCES").exists()
    except Exception:
        return False

def _admin_allowed(user) -> bool:
    return (
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or _in_admin_group(user)
        )
    )

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return _admin_allowed(self.request.user)
    def handle_no_permission(self):
        return redirect("administracion:login")

class OTPRequiredMixin(StaffRequiredMixin):
    """Exige 2FA (TOTP) para acceder al panel."""
    @method_decorator(otp_required(login_url=reverse_lazy("two_factor:login")))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


# =========================== Home ===========================

class AdminHomeView(LoginRequiredMixin, TemplateView):
    template_name = "administracion/home.html"
    login_url = "administracion:login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_requests"] = Request.objects.count()
        ctx["pending"] = Request.objects.filter(status="pending").count()
        ctx["accepted"] = Request.objects.filter(status="accepted").count()
        ctx["rejected"] = Request.objects.filter(status="rejected").count()
        ctx["total_graduates"] = Graduate.objects.count()

        q = (self.request.GET.get("q") or "").strip()
        ctx["q"] = q
        qs = Request.objects.select_related("program").order_by("-sent_at")
        if q:
            qs = qs.filter(
                Q(email__icontains=q) |
                Q(curp__icontains=q) |
                Q(name__icontains=q) |
                Q(lastname__icontains=q) |
                Q(program__name__icontains=q)
            )

        ctx["recent_requests"] = qs[:20]
        ctx["recent_logs"] = AdminAccessLog.objects.select_related("user").order_by("-created_at")[:12]
        ctx["now"] = timezone.now()

        try:
            ctx["user_groups"] = list(self.request.user.groups.values_list("name", flat=True))
        except Exception:
            ctx["user_groups"] = None

        ctx["csrf_token"] = get_token(self.request)
        return ctx


# ======================= Login / Logout =======================

class AdminLoginView(FormView):
    template_name = "administracion/login.html"
    form_class = AdminLoginForm
    success_url = reverse_lazy("administracion:home")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        email = self.request.POST.get("email") or ""
        fails = failed_attempts_count(self.request, username_or_email=email)
        ctx["show_hcaptcha"] = fails >= getattr(settings, "HCAPTCHA_THRESHOLD_FAILS", 3)
        ctx["HCAPTCHA_SITE_KEY"] = getattr(settings, "HCAPTCHA_SITE_KEY", "")
        return ctx

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("administracion:home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        remember = form.cleaned_data["remember_me"]
        needs_captcha = failed_attempts_count(
            self.request, username_or_email=email
        ) >= getattr(settings, "HCAPTCHA_THRESHOLD_FAILS", 3)

        if needs_captcha:
            token = self.request.POST.get("h-captcha-response", "")
            if not token:
                form.add_error(None, "Por favor, completa la verificación.")
                return self.form_invalid(form)
            secret = getattr(settings, "HCAPTCHA_SECRET_KEY", "")
            try:
                resp = requests.post(
                    "https://hcaptcha.com/siteverify",
                    data={
                        "secret": secret,
                        "response": token,
                        "remoteip": self.request.META.get("REMOTE_ADDR", ""),
                    },
                    timeout=5,
                )
                data = resp.json()
                if not data.get("success"):
                    form.add_error(None, "Verificación fallida. Intenta de nuevo.")
                    return self.form_invalid(form)
            except Exception:
                form.add_error(None, "No pudimos validar el captcha. Intenta de nuevo.")
                return self.form_invalid(form)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user = None

        auth_user = authenticate(
            self.request,
            username=getattr(user, "username", email),
            password=password
        ) if user else None

        if not auth_user or not auth_user.is_active or not _admin_allowed(auth_user):
            form.add_error(None, "Credenciales inválidas.")
            return self.form_invalid(form)

        login(self.request, auth_user)

        if remember:
            self.request.session.set_expiry(int(timedelta(hours=8).total_seconds()))
            self.request.session["remember_me"] = True
        else:
            self.request.session.set_expiry(0)
            self.request.session["remember_me"] = False

        return super().form_valid(form)

class AdminLogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("administracion:login")


# ================ Password reset (plantillas personalizadas) ================

class AdminPasswordResetView(PasswordResetView):
    template_name = "administracion/password_reset.html"
    email_template_name = "administracion/password_reset_email.txt"
    subject_template_name = "administracion/password_reset_subject.txt"
    success_url = reverse_lazy("administracion:password_reset_done")

class AdminPasswordResetDoneView(PasswordResetDoneView):
    template_name = "administracion/password_reset_done.html"

class AdminPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "administracion/password_reset_confirm.html"
    success_url = reverse_lazy("administracion:password_reset_complete")

class AdminPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "administracion/password_reset_complete.html"


# =========================== Endpoints AJAX (cuenta) ===========================

@require_POST
def password_change_inline(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "No autenticado."}, status=401)

    p1 = (request.POST.get("new_password1") or "").strip()
    p2 = (request.POST.get("new_password2") or "").strip()

    if not p1 or not p2:
        return JsonResponse({"ok": False, "error": "Completa ambos campos."}, status=400)
    if p1 != p2:
        return JsonResponse({"ok": False, "error": "Las contraseñas no coinciden."}, status=400)
    if len(p1) < 8:
        return JsonResponse({"ok": False, "error": "La contraseña debe tener al menos 8 caracteres."}, status=400)

    user = request.user
    user.set_password(p1)
    user.save()
    update_session_auth_hash(request, user)
    return JsonResponse({"ok": True})

@require_POST
def create_admin_inline(request):
    me = request.user
    if not _admin_allowed(me):
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    email = (request.POST.get("email") or "").strip().lower()
    username = (request.POST.get("username") or "").strip()
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    pw1 = (request.POST.get("password1") or "").strip()
    pw2 = (request.POST.get("password2") or "").strip()

    if not email or "@" not in email:
        return JsonResponse({"ok": False, "error": "Email inválido."}, status=400)
    if pw1 != pw2 or len(pw1) < 8:
        return JsonResponse({"ok": False, "error": "La contraseña no es válida o no coincide."}, status=400)

    if not username:
        base = slugify(email.split("@")[0]) or "admin"
        candidate, i = base, 1
        while User.objects.filter(username=candidate).exists():
            i += 1
            candidate = f"{base}{i}"
        username = candidate

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"ok": False, "error": "Ya existe un usuario con ese email."}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"ok": False, "error": "El nombre de usuario ya está en uso."}, status=400)

    u = User.objects.create_user(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        password=pw1,
        is_active=True,
    )

    if hasattr(u, "is_staff"):
        u.is_staff = True
        u.save(update_fields=["is_staff"])

    grp, _ = Group.objects.get_or_create(name="AdministradoresCES")
    u.groups.add(grp)

    return JsonResponse({"ok": True, "user": {"id": u.id, "username": u.username, "email": u.email}})


# ======================== Plantillas (portada) ========================

@login_required
def plantillas(request, req_id=None):
    generating = (
        Request.objects
        .filter(status='generating')
        .select_related('program')
        .order_by('-sent_at')
    )

    active_req = None
    if req_id:
        active_req = get_object_or_404(
            Request.objects.select_related('program'),
            pk=req_id
        )

    full_name = ""
    program_name = ""
    active_rfc = ""
    active_curp = ""
    active_job_title = ""
    active_industry = ""

    if active_req:
        first = getattr(active_req, "name", "") or ""
        last = getattr(active_req, "lastname", "") or ""
        full_name = f"{first} {last}".strip()
        prog = getattr(active_req, "program", None)
        program_name = getattr(prog, "name", "") if prog else ""
        active_rfc = getattr(active_req, "rfc", "") or ""
        active_curp = getattr(active_req, "curp", "") or ""
        active_job_title = getattr(active_req, "job_title", "") or ""
        active_industry = getattr(active_req, "industry", "") or ""

    ctx = {
        'generating_reqs': generating,
        'active_req': active_req,
        'full_name': full_name,
        'program_name': program_name,
        'active_rfc': active_rfc,
        'active_curp': active_curp,
        'active_job_title': active_job_title,
        'active_industry': active_industry,
        'diploma': {},
        'dc3': {},
        'cproem': {},
    }
    return render(request, 'administracion/plantillas.html', ctx)


# ============================= Egresados =============================

def _random_hex_25() -> str:
    return secrets.token_hex(13)[:25]

def _qr_png_data_url(payload: str, box_size: int = 12, border: int = 2) -> str:
    qr = qrcode.QRCode(version=None, box_size=box_size, border=border)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buff = io.BytesIO()
    img.save(buff, format="PNG")
    return "data:image/png;base64," + b64encode(buff.getvalue()).decode("ascii")

def _constancia_tipo(program) -> str:
    name = (getattr(program, "name", "") or "").lower()
    if "cproem" in name:
        return "cproem"
    return "dc3"

def _pick(*vals):
    for v in vals:
        if v:
            return v
    return None

def _get_tipo_from_request(request, default="diploma"):
    return (request.GET.get("tipo")
            or request.GET.get("type")
            or request.POST.get("tipo")
            or request.POST.get("type")
            or default)

def _norm_txt(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def _map_admin_constancia_type(val) -> str:
    """
    Mapea un valor de constancia_type (enum/int/str) a 'cproem' o 'dc3'.
    """
    if val is None:
        return ""
    try:
        from .models import ConstanciaType as _CT
        raw = getattr(val, "value", val)
        if isinstance(raw, int):
            if getattr(_CT, "CEPROEM", None) == raw:
                return "cproem"
            if getattr(_CT, "DC3", None) == raw:
                return "dc3"
        sval = _norm_txt(str(raw))
        if "cproem" in sval or "ceproem" in sval:
            return "cproem"
        if "dc3" in sval:
            return "dc3"
    except Exception:
        sval = _norm_txt(str(getattr(val, "value", val)))
        if "cproem" in sval or "ceproem" in sval:
            return "cproem"
        if "dc3" in sval:
            return "dc3"
    return ""
def _constancia_kind_by_fields(req) -> str | None:
    """
    Aplica tu regla por presencia de campos.
    - Solo CURP (y sin RFC/puesto/giro/razón_social) => 'cproem'
    - Si hay cualquiera de los otros => 'dc3'
    Devuelve None si no puede decidir.
    """
    if not req:
        return None
    curp = (getattr(req, "curp", "") or "").strip()
    rfc = (getattr(req, "rfc", "") or "").strip()
    job = (getattr(req, "job_title", "") or "").strip()
    ind = (getattr(req, "industry", "") or "").strip()
    biz = (getattr(req, "business_name", "") or "").strip()

    has_extras = any([rfc, job, ind, biz])
    if curp and not has_extras:
        return "cproem"
    if has_extras:
        return "dc3"
    return None

def constancia_kind_for_request(obj) -> str:
    """
    Decide 'cproem' o 'dc3'.
    - Si obj es Request, primero respetamos Program si lo define claramente.
    - Regla de negocio: si SOLO hay CURP (y NO hay rfc, job_title, industry, business_name) => cproem.
      Si existen cualquiera de esos campos => dc3.
    """
    try:
        program = getattr(obj, "program", None)
    except Exception:
        program = None

    # 1) Lo que diga el programa (si aplica)
    kind = _program_constancia_kind(program)  # tu helper existente: 'dc3' | 'cproem'

    # 2) Validación por datos del alumno (regla tuya)
    curp = getattr(obj, "curp", None) if hasattr(obj, "curp") else None
    rfc = getattr(obj, "rfc", None) if hasattr(obj, "rfc") else None
    job = getattr(obj, "job_title", None) if hasattr(obj, "job_title") else None
    giro = getattr(obj, "industry", None) if hasattr(obj, "industry") else None
    biz  = getattr(obj, "business_name", None) if hasattr(obj, "business_name") else None

    # Si solo hay CURP y no hay nada más laboral → CPROEM (gana la regla de negocio)
    if curp and not any([rfc, job, giro, biz]):
        return "cproem"

    return kind or "dc3"

def _program_constancia_kind(program) -> str:
    """
    Devuelve 'cproem' o 'dc3' según:
    1) constancia_type en el propio objeto (si existe)
    2) cross-lookup en administracion.Program por code o name
    3) heurística por texto (name/code/abbreviation)
    4) fallback 'dc3'
    """
    if not program:
        return "dc3"

    # 1) Si el objeto trae constancia_type directo (caso ProgramAdmin)
    ct = getattr(program, "constancia_type", None)
    kind = _map_admin_constancia_type(ct)
    if kind:
        return kind

    # 2) Cross-lookup contra ProgramAdmin si lo tenemos disponible
    try:
        from .models import Program as ProgramAdmin
        code = getattr(program, "code", None)
        name = getattr(program, "name", None)

        cand = None
        if code:
            cand = ProgramAdmin.objects.filter(code__iexact=code).first()
        if not cand and name:
            cand = ProgramAdmin.objects.filter(name__iexact=name).first()

        if cand:
            kind = _map_admin_constancia_type(getattr(cand, "constancia_type", None))
            if kind:
                return kind
    except Exception:
        pass  # si falla el lookup, seguimos a heurística

    # 3) Heurística por texto (soporta CPROEM/CEPROEM)
    for attr in ("name", "code", "abbreviation"):
        sval = _norm_txt(getattr(program, attr, ""))
        if "cproem" in sval or "ceproem" in sval:
            return "cproem"

    # 4) Fallback
    return "dc3"

# Alias usado por el resto del código
def _constancia_tipo(program) -> str:
    return _program_constancia_kind(program)

@login_required
@csp_update({
    'img-src': ("'self'", "data:", "blob:"),
    'style-src': ("'self'", "https://fonts.googleapis.com", csp.NONCE),
})
def egresados(request, req_id=None):
    """
    Página del panel de egresados. Decide si la constancia del programa activo
    es DC3 o CPROEM y expone flags/etiquetas al template.
    """
    generating = (
        Request.objects
        .filter(status='generating')
        .select_related('program')
        .order_by('-sent_at')
    )

    active_req = get_object_or_404(
        Request.objects.select_related('program'),
        pk=req_id
    ) if req_id else None

    # Datos básicos mostrados/ editables
    program_name   = getattr(getattr(active_req, 'program', None), 'name', None) if active_req else None
    req_start      = getattr(active_req, 'start_date', None) if active_req else None
    req_end        = getattr(active_req, 'end_date', None) if active_req else None
    curp           = getattr(active_req, 'curp', None) if active_req else None
    rfc            = getattr(active_req, 'rfc', None) if active_req else None
    job_title      = getattr(active_req, 'job_title', None) if active_req else None
    industry       = getattr(active_req, 'industry', None) if active_req else None
    business_name  = getattr(active_req, 'business_name', None) if active_req else None  # Razón social (DC3)

    # Tipo de constancia según el programa
    const_kind = constancia_kind_for_request(active_req) if active_req else "dc3"
    is_dc3     = const_kind == "dc3"
    is_cproem  = const_kind == "cproem"
    const_label = "Constancia DC3" if is_dc3 else "Constancia CPROEM"

    ctx = {
        'generating_reqs': generating,
        'active_req': active_req,

        # Datos para diplomas/constancias
        'program_name': program_name,
        'req_start': req_start,
        'req_end': req_end,

        'curp': curp,
        'rfc': rfc,
        'job_title': job_title,
        'industry': industry,
        'business_name': business_name,

        # Flags / etiquetas para el template
        'is_dc3': is_dc3,
        'is_cproem': is_cproem,
        'constancia_label': const_label,
        'const_kind': const_kind,
        # CSRF para el JS
        'csrf_token': get_token(request),
    }
    return render(request, "administracion/egresados.html", ctx)

@csp_update({
    'img-src': ("'self'", "data:", "blob:"),
    'style-src': ("'self'", "https://fonts.googleapis.com", csp.NONCE),
})
@require_GET
def egresados_preview_pdf(request, req_id: int):
    req = get_object_or_404(Request.objects.select_related("program"), pk=req_id)

    # 1) Determinar tipo real
    tipo_query = _get_tipo_from_request(request, default="diploma")
    if tipo_query not in ("diploma", "constancia"):
        raise Http404()

    tipo_real = "diploma" if tipo_query == "diploma" else constancia_kind_for_request(req)

    # (opcional) logging para depurar
    try:
        log.info(
            "Preview ↦ tipo=%s (req=%s, prog=%s)",
            tipo_real, req.id, getattr(getattr(req, "program", None), "name", None)
        )
    except Exception:
        pass

    # 2) Resolver plantilla + contexto
    tpl, ctx = _render_ctx_and_template(
        request, req, tipo_real, use_published_if_exists=True
    )

    try:
        # 3) Render HTML → PDF (WeasyPrint)  ⬅️ AQUÍ VA EL SNIPPET
        from weasyprint import HTML
        html = render_to_string(tpl, ctx, request=request)
        pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

        # 4) Endurecer + marca de agua (opcional)
        pdf_bytes = _pdf_secure(
            pdf_bytes,
            user_pwd="",                         # sin pass para abrir en visor
            watermark_text="CES · Solo lectura"  # marca de agua (opcional)
        )

        # 5) Responder
        return FileResponse(
            io.BytesIO(pdf_bytes),
            content_type="application/pdf",
            filename=f"{tipo_real}-{req.id}.pdf",
        )

    except Exception:
        # Fallback: muestra HTML si WeasyPrint no está instalado
        html = render_to_string(tpl, ctx, request=request)
        return HttpResponse("WeasyPrint no está instalado. Vista HTML abajo:<hr>" + html)

@login_required
def egresado_update(request, req_id: int):
    """Actualiza campos simples de Egresado vía POST (AJAX)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    Egresado = apps.get_model("administracion", "Egresado")
    if Egresado is None:
        return HttpResponseBadRequest("Modelo Egresado no encontrado")

    allowed = {
        "nombre", "apellido_paterno", "apellido_materno",
        "curp", "rfc", "nss", "telefono", "email", "status", "notas",
    }
    data = {k: v for k, v in request.POST.items() if k in allowed}
    if not data:
        return HttpResponseBadRequest("Sin campos válidos")

    obj = get_object_or_404(Egresado, pk=req_id)
    for k, v in data.items():
        setattr(obj, k, v)
    obj.save()
    return JsonResponse({"ok": True, "id": obj.pk, "saved": data})

@login_required
def egresado_update_inline(request, req_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    incoming = {k: v for k, v in request.POST.items() if k in ALLOWED_EGRESADO_FIELDS}

    if Egresado is not None:
        obj = get_object_or_404(Egresado, pk=req_id)
        for field, value in incoming.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        obj.save()
        return JsonResponse({"ok": True, "id": obj.pk, "saved": incoming})

    return JsonResponse({
        "ok": True,
        "id": req_id,
        "saved": incoming,
        "note": "Egresado model no disponible; stub.",
    })

@require_POST
def doc_send(request, req_id):
    import logging
    log = logging.getLogger(__name__)

    req = get_object_or_404(Request.objects.select_related("program"), pk=req_id)

    # --- Tipo solicitado (query) y tipo real ---
    tipo_query = _get_tipo_from_request(request, default="diploma")
    if tipo_query not in ("diploma", "constancia"):
        return JsonResponse({"ok": False, "error": "Tipo inválido."}, status=400)

    tipo_real = "diploma" if tipo_query == "diploma" else constancia_kind_for_request(req)

    # --- Logging ---
    log.info("[doc_send] tipo_query=%s → tipo_real=%s (req=%s)", tipo_query, tipo_real, req.id)

    # --- Publicar token / URL de verificación ---
    doc = _ensure_published_token(req, tipo_real)
    verify_url = request.build_absolute_uri(reverse("administracion:verificar_token", args=[doc.token]))

    return JsonResponse({"ok": True, "verify_url": verify_url, "tipo": tipo_real})

@require_POST
def doc_confirm(request, req_id):
    import logging
    log = logging.getLogger(__name__)

    req = get_object_or_404(Request.objects.select_related("program"), pk=req_id)

    # --- Tipo solicitado (query) y tipo real ---
    tipo_query = _get_tipo_from_request(request, default="constancia")
    if tipo_query not in ("diploma", "constancia"):
        return JsonResponse({"ok": False, "error": "Tipo inválido."}, status=400)

    tipo_real = "diploma" if tipo_query == "diploma" else constancia_kind_for_request(req)

    # --- Logging ---
    log.info("[doc_confirm] tipo_query=%s → tipo_real=%s (req=%s)", tipo_query, tipo_real, req.id)

    # --- Publicar token / URL de verificación ---
    doc = _ensure_published_token(req, tipo_real)
    verify_url = request.build_absolute_uri(reverse("administracion:verificar_token", args=[doc.token]))

    return JsonResponse({"ok": True, "verify_url": verify_url, "tipo": tipo_real})

def doc_preview(request, req_id):
    return egresados_preview_pdf(request, req_id)

@require_GET
def doc_download(request, req_id: int):
    """
    Descarga el documento del egresado:
      - ?tipo=diploma|constancia
      - ?fmt=pdf|docx|zip
    PDF se genera con WeasyPrint y se endurece con _pdf_secure().
    DOCX se genera con python-docx (formato simple).
    ZIP incluye ambos (si alguno falla, añade un README con la razón).
    """
    # --- 1) Obtener registro y parámetros ---
    req = get_object_or_404(Request.objects.select_related("program"), pk=req_id)

    tipo = (request.GET.get("tipo") or "diploma").lower()
    if tipo not in ("diploma", "constancia"):
        return JsonResponse({"ok": False, "error": "Tipo inválido."}, status=400)

    fmt = (request.GET.get("fmt") or "pdf").lower()
    if fmt not in ("pdf", "docx", "zip"):
        return JsonResponse({"ok": False, "error": "Formato inválido."}, status=400)

    # Determinar si la constancia es dc3 o cproem
    tipo_real = "diploma" if tipo == "diploma" else constancia_kind_for_request(req)

    # Publicar token (si aplica para constancias/diplomas publicados)
    try:
        _ensure_published_token(req, tipo_real)
    except Exception:
        # No es crítico para descarga; sólo logueamos
        log.exception("No se pudo asegurar token publicado para %s #%s", tipo_real, req.id)

    # --- 2) Datos comunes para DOCX y para render de plantilla ---
    program_name = getattr(getattr(req, "program", None), "name", "") or "—"
    full_name = f"{getattr(req, 'name', '') or ''} {getattr(req, 'lastname', '') or ''}".strip()
    start_date = getattr(req, "start_date", None)
    end_date = getattr(req, "end_date", None)

    def _fmt_date(d):
        try:
            return d.strftime("%d/%m/%Y") if d else "—"
        except Exception:
            return str(d) if d else "—"

    # --- 3) Helpers internos ---

    def _make_pdf_bytes():
        """Renderiza la plantilla HTML → PDF (WeasyPrint) y aplica _pdf_secure."""
        # Traer plantilla y contexto ya listos
        tpl, ctx = _render_ctx_and_template(
            request, req, tipo_real, use_published_if_exists=True
        )
        # Render → PDF
        try:
            from weasyprint import HTML
        except Exception as e:
            raise RuntimeError(f"WeasyPrint no está instalado: {e}")

        html = render_to_string(tpl, ctx, request=request)
        raw_pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

        # Endurecer / marcas (ajusta a lo que quieras)
        secured = _pdf_secure(
            raw_pdf,
            user_pwd="",  # apertura sin password en visor
            watermark_text="CES · Solo lectura",
        )
        return secured

    def _make_docx_bytes():
        """Construye un DOCX simple con python-docx."""
        try:
            from docx import Document
        except Exception as e:
            raise RuntimeError(f"python-docx no está instalado: {e}")

        doc = Document()
        doc.add_heading(f"{tipo_real.upper()} - {program_name}", level=1)
        doc.add_paragraph(f"Nombre: {full_name or '—'}")
        doc.add_paragraph(f"Programa: {program_name}")
        doc.add_paragraph(f"Inicio: {_fmt_date(start_date)}")
        doc.add_paragraph(f"Fin: {_fmt_date(end_date)}")

        # Campos extra de DC3 si existen
        curp = getattr(req, "curp", None)
        rfc  = getattr(req, "rfc", None)
        job  = getattr(req, "job_title", None)
        giro = getattr(req, "industry", None)
        biz  = getattr(req, "business_name", None)

        if curp: doc.add_paragraph(f"CURP: {curp}")
        if rfc:  doc.add_paragraph(f"RFC: {rfc}")
        if job:  doc.add_paragraph(f"Puesto: {job}")
        if giro: doc.add_paragraph(f"Giro: {giro}")
        if biz:  doc.add_paragraph(f"Razón social: {biz}")

        doc.add_paragraph("")
        doc.add_paragraph("Documento generado automáticamente por CES System.")

        b = io.BytesIO()
        doc.save(b)
        b.seek(0)
        return b.getvalue()

    # --- 4) Ramas por formato solicitado ---

    if fmt == "pdf":
        try:
            pdf_bytes = _make_pdf_bytes()
            return FileResponse(
                io.BytesIO(pdf_bytes),
                content_type="application/pdf",
                filename=f"{tipo_real}-{req.id}.pdf",
            )
        except Exception as e:
            log.exception("Fallo generando PDF")
            return JsonResponse({"ok": False, "error": f"Error generando PDF: {e}"}, status=500)

    elif fmt == "docx":
        try:
            docx_bytes = _make_docx_bytes()
            return FileResponse(
                io.BytesIO(docx_bytes),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                filename=f"{tipo_real}-{req.id}.docx",
            )
        except Exception as e:
            log.exception("Fallo generando DOCX")
            return JsonResponse({"ok": False, "error": f"Error generando DOCX: {e}"}, status=500)

    else:  # fmt == "zip"
        # Intentamos generar ambos; si alguno falla, lo omitimos y añadimos README.txt
        readme_lines = []
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
            # DOCX
            try:
                docx_bytes = _make_docx_bytes()
                zf.writestr(f"{tipo_real}-{req.id}.docx", docx_bytes)
            except Exception as e:
                msg = f"[DOCX] No se pudo generar: {e}"
                log.exception(msg)
                readme_lines.append(msg)

            # PDF
            try:
                pdf_bytes = _make_pdf_bytes()
                zf.writestr(f"{tipo_real}-{req.id}.pdf", pdf_bytes)
            except Exception as e:
                msg = f"[PDF] No se pudo generar: {e}"
                log.exception(msg)
                readme_lines.append(msg)

            if readme_lines:
                zf.writestr(
                    "README.txt",
                    "Algunos archivos no se pudieron generar:\n\n" + "\n".join(readme_lines)
                )

        mem.seek(0)
        return FileResponse(
            mem,
            content_type="application/zip",
            filename=f"{tipo_real}-{req.id}.zip",
        )

# ========================= Verificación =========================

def verificar_token(request, token: str):
    dt = get_object_or_404(DocToken, token=token, is_active=True)
    req = dt.request
    ctx = {
        "token": token,
        "tipo": dt.tipo,
        "alumno": f"{getattr(req,'name','')} {getattr(req,'lastname','')}".strip(),
        "programa": getattr(getattr(req, "program", None), "name", "—"),
        "inicio": getattr(req, "start_date", None),
        "fin": getattr(req, "end_date", None),
    }
    return render(request, "administracion/verify_result.html", ctx)


# ====================== Tokens helpers ======================

def _ensure_published_token(req: Request, tipo: str) -> DocToken:
    try:
        return DocToken.objects.get(request=req, tipo=tipo, is_active=True)
    except DocToken.DoesNotExist:
        token = _random_hex_25()
        return DocToken.objects.create(request=req, tipo=tipo, token=token, is_active=True)

def _get_existing_token(req: Request, tipo: str):
    try:
        return DocToken.objects.get(request=req, tipo=tipo, is_active=True)
    except DocToken.DoesNotExist:
        return None


# ====================== Render helpers (ctx/plantilla/PDF/DOCX) ======================

def _render_ctx_and_template(request, req, tipo_real: str, *, use_published_if_exists: bool):
    nombre = f"{getattr(req,'name','')} {getattr(req,'lastname','')}".strip()
    programa = getattr(getattr(req, "program", None), "name", "")

    if use_published_if_exists:
        published = _get_existing_token(req, tipo_real)
        token = published.token if published else _random_hex_25()
    else:
        token = _random_hex_25()

    verify_url = request.build_absolute_uri(
        reverse("administracion:verificar_token", args=[token])
    )
    qr_url = _qr_png_data_url(verify_url, box_size=12)

    if tipo_real == "diploma":
        tpl = "administracion/pdf_diploma.html"
        ctx = {
            "folio": f"DIP-{req.id:06d}",
            "nombre": nombre,
            "programa": programa,
            "inicio": getattr(req, "start_date", None),
            "fin": getattr(req, "end_date", None),
            "qr_url": qr_url,
        }
    else:
        tpl = "administracion/pdf_constancia_dc3.html" if tipo_real == "dc3" else "administracion/pdf_constancia_cproem.html"
        ctx = {
        "folio": f"CON-{req.id:06d}",
        "nombre": nombre,
        "programa": programa,
        "inicio": getattr(req, "start_date", None),
        "fin": getattr(req, "end_date", None),
        "curp": getattr(req, "curp", None),
        "rfc": getattr(req, "rfc", None),
        "puesto": getattr(req, "job_title", None),
        "giro": getattr(req, "industry", None),

        # 🔹 NUEVOS CAMPOS PARA DC-3:
        "razon_social": getattr(req, "business_name", None),
        "horas": getattr(req, "hours", None),  # si no existe en tu modelo, puedes quitar esta línea

        "qr_url": qr_url,
        }
    return tpl, ctx


# ==================== Seguridad PDF ====================

def _pdf_secure(pdf_bytes: bytes, *, user_pwd: str = "", watermark_text: Optional[str] = None) -> bytes:
    """
    Endurece el PDF:
      1) Rasteriza cada página (PyMuPDF) → dificulta edición/extracción.
      2) Aplica marca de agua diagonal (opcional) con Pillow.
      3) Cifra con pikepdf, bloqueando copiar/modificar/imprimir.
    Si alguna lib falta, hace "best effort" con lo disponible.
    """
    working_pdf = pdf_bytes

    # 1) Rasterización y marca de agua (opcional)
    try:
        import fitz  # PyMuPDF
        from PIL import Image, ImageDraw, ImageFont

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        mat = fitz.Matrix(2, 2)  # ~144 dpi
        frames = []
        for i in range(doc.page_count):
            pix = doc.load_page(i).get_pixmap(matrix=mat, alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            if watermark_text:
                W, H = im.size
                draw = ImageDraw.Draw(im)
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None

                # Capa temporal RGBA para simular transparencia
                wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                wmdraw = ImageDraw.Draw(wm)

                text = str(watermark_text)
                # Repetir texto diagonalmente
                step = max(240, int(min(W, H) / 4))
                angle = -30
                # Dibuja líneas de texto antes de rotar, luego rota la capa
                for y in range(0, H + step, step):
                    for x in range(-W, W, step):
                        wmdraw.text((x, y), text, fill=(180, 180, 180, 70), font=font)

                wm = wm.rotate(angle, expand=1)
                # Centrar la marca rotada sobre el lienzo
                x0 = (W - wm.width) // 2
                y0 = (H - wm.height) // 2
                im = im.convert("RGBA")
                im.alpha_composite(wm, (x0, y0))
                im = im.convert("RGB")

            frames.append(im)

        doc.close()
        if frames:
            out = io.BytesIO()
            frames[0].save(out, format="PDF", save_all=True, append_images=frames[1:])
            working_pdf = out.getvalue()
    except Exception:
        # Si falla PyMuPDF/Pillow, seguimos con el original
        pass

    # 2) Cifrado + permisos con pikepdf
    try:
        import pikepdf, inspect

        desired = {
            "print_lowres": False,
            "print_highres": False,
            "extract": False,       # copiar/extraer
            "modify": False,
            "annotate": False,
            "form": False,
            "assemble": False,
            "accessibility": False, # pon True si requieres accesibilidad
        }
        perm_params = set(inspect.signature(pikepdf.Permissions).parameters.keys())
        perms = pikepdf.Permissions(**{k: v for k, v in desired.items() if k in perm_params})

        enc = pikepdf.Encryption(
            user=(user_pwd or ""),          # "" = abre sin pedir pass
            owner=secrets.token_hex(16),    # owner aleatorio
            R=6,                            # AES-256
            allow=perms
        )

        out = io.BytesIO()
        with pikepdf.open(io.BytesIO(working_pdf)) as pdf:
            pdf.save(out, encryption=enc)
        return out.getvalue()
    except Exception:
        # Si no hay pikepdf, devolvemos lo rasterizado/marcado
        return working_pdf
# ================== Catálogo simple ==================

def plantillas_catalogo(request):
    return render(request, "administracion/plantillas_catalogo.html")


# ================== Tablero de solicitudes ==================

class RequestsBoardView(LoginRequiredMixin, TemplateView):
    template_name = "administracion/solicitudes.html"
    login_url = "administracion:login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Filtros por querystring (compat: 'estado' o 'status')
        q = (self.request.GET.get("q") or "").strip()
        estado = (self.request.GET.get("estado") or self.request.GET.get("status") or "pending").strip() or "pending"
        program_id = (self.request.GET.get("program") or "").strip()

        # Base queryset
        base = Request.objects.select_related("program")

        if q:
            base = base.filter(
                Q(email__icontains=q) |
                Q(name__icontains=q) |
                Q(lastname__icontains=q) |
                Q(program__name__icontains=q)
            )

        if program_id:
            base = base.filter(program_id=program_id)

        # Orden por estado
        if estado == "pending":
            qs = base.filter(status="pending").order_by("sent_at")
        elif estado in {"accepted", "rejected", "generating", "review"}:
            qs = base.filter(status=estado).order_by("-sent_at")
        else:
            qs = base.order_by("-sent_at")

        # Resolver nombre de programa desde default (ces_db)
        qs_list = list(qs)
        missing_ids = {
            r.program_id
            for r in qs_list
            if getattr(r, "program_id", None) and (getattr(r, "program", None) is None
                                                   or not getattr(getattr(r, "program", None), "name", None))
        }

        sim_map = {}
        if missing_ids:
            sim_programs = ProgramSim.objects.filter(id__in=missing_ids).only("id", "name")
            sim_map = {p.id: getattr(p, "name", "") for p in sim_programs}

        for r in qs_list:
            name = None
            if getattr(r, "program", None) and getattr(r.program, "name", None):
                name = r.program.name
            elif r.program_id:
                name = sim_map.get(r.program_id)
            setattr(r, "program_name", name or "Sin programa")

        items = qs_list

        # Contadores por estado
        all_counts = Request.objects.values("status").annotate(total=Count("id"))
        counts = {c["status"]: c["total"] for c in all_counts}

        # Catálogo de programas (default)
        programas = list(
            ProgramSim.objects.all()
            .order_by("name")
            .values("id", "name", "abbreviation")
        )

        statuses = [
            ("pending", "Pendiente"),
            ("review", "Revisión"),
            ("accepted", "Aprobada"),
            ("rejected", "Rechazada"),
            ("generating", "Generando"),
        ]

        ctx.update({
            "q": q,
            "estado": estado,
            "status": estado,
            "program_id": program_id,
            "items": items,
            "programas": programas,
            "counts": counts,
            "count_pending": counts.get("pending", 0),
            "statuses": statuses,
            "now": timezone.now(),
        })

        ctx["csrf_token"] = get_token(self.request)
        ctx["requests_update_url"] = reverse("administracion:request_update_status")
        return ctx


@require_POST
def request_update_status(request):
    me = request.user
    if not me.is_authenticated:
        return JsonResponse({"ok": False, "msg": "No autenticado."}, status=401)
    if not _admin_allowed(me):
        return JsonResponse({"ok": False, "msg": "No autorizado."}, status=403)

    rid = request.POST.get("id")
    action = (request.POST.get("action") or "").strip()
    reason = (request.POST.get("reason") or "").strip()

    STATUS_MAP = {
        "to_review":  "review",
        "approve":    "accepted",
        "reject":     "rejected",
        "generating": "generating",
    }
    if not rid or action not in STATUS_MAP:
        return JsonResponse({"ok": False, "msg": "Parámetros inválidos."}, status=400)

    try:
        req_obj = Request.objects.get(pk=rid)
    except Request.DoesNotExist:
        return JsonResponse({"ok": False, "msg": "Solicitud no encontrada."}, status=404)

    new_status = STATUS_MAP[action]

    if new_status == "rejected" and not reason:
        return JsonResponse({"ok": False, "msg": "Falta el motivo de rechazo."}, status=400)

    if new_status == "rejected":
        req_obj.status_reason = reason
        req_obj.status = new_status
        req_obj.save(update_fields=["status", "status_reason"])
    else:
        req_obj.status = new_status
        req_obj.save(update_fields=["status"])

    if not RequestEvent.objects.filter(request=req_obj, status=new_status).exists():
        RequestEvent.objects.create(request=req_obj, status=new_status, note=(reason or None))

    return JsonResponse({"ok": True, "new_status": new_status})


# ===================== (NUEVO) Guardar edición inline =====================

@login_required
@require_http_methods(["POST"])
def egresado_update_inline(request, req_id: int):
    """Actualiza campos básicos del Request desde Egresados (edición inline)."""
    if not _admin_allowed(request.user):
        return JsonResponse({"ok": False, "msg": "No autorizado."}, status=403)

    req_obj = get_object_or_404(Request, pk=req_id)

    # Import local para no tocar cabecera
    from django.utils.dateparse import parse_date

    allowed = ("name","lastname","curp","rfc","job_title","industry","business_name","start_date","end_date")
    changed = {}

    for f in allowed:
        val = (request.POST.get(f) or "").strip()
        if f in ("start_date", "end_date"):
            new_val = parse_date(val) if val else None
            if val and new_val is None:
                return JsonResponse({"ok": False, "msg": f"Fecha inválida en {f} (use YYYY-MM-DD)."}, status=400)
            old_val = getattr(req_obj, f, None)
            if old_val != new_val:
                setattr(req_obj, f, new_val)
                changed[f] = new_val.isoformat() if new_val else ""
        else:
            old_text = getattr(req_obj, f, "") or ""
            if val != old_text:
                setattr(req_obj, f, val)
                changed[f] = val

    if changed:
        req_obj.save(update_fields=list(changed.keys()))
        # Registrar un evento suave (opcional, no afecta flujos)
        if not RequestEvent.objects.filter(request=req_obj, status="review").exists():
            RequestEvent.objects.create(request=req_obj, status="review", note="Edición de datos (admin)")

    return JsonResponse({"ok": True, "changed": changed})


# ================== PLANTILLAS PREMIUM ==================

@login_required
def plantillas_admin(request):
    q = request.GET.get("q", "").strip()
    qs = DesignTemplate.objects.all().order_by("-updated_at")
    if q:
        qs = qs.filter(title__icontains=q)
    return render(request, "administracion/plantillas_admin.html", {"items": qs, "q": q})

@login_required
@require_http_methods(["GET", "POST"])
def plantilla_create(request):
    if request.method == "POST":
        title = request.POST.get("title") or "Nueva plantilla"
        kind = (request.POST.get("kind") or DesignTemplate.DESIGN).lower()
        raw = (request.POST.get("json") or "").strip()

        if not raw:
            data = {"pages": [{"width": 1920, "height": 1080, "background": "#ffffff", "layers": []}]}
        else:
            try:
                data = json.loads(raw)
                pages = data.get("pages") or []
                if not pages:
                    raise json.JSONDecodeError("Debe existir pages[0] con width/height/background.", raw, 0)
                p0 = pages[0]
                if not isinstance(p0.get("width"), (int, float)) or not isinstance(p0.get("height"), (int, float)):
                    raise json.JSONDecodeError("width y height deben ser numéricos.", raw, 0)
                if not isinstance(p0.get("background"), str):
                    raise json.JSONDecodeError('background debe ser string (ej. "#ffffff").', raw, 0)
            except json.JSONDecodeError as e:
                return render(
                    request,
                    "administracion/plantilla_form.html",
                    {"mode": "create", "form_error": str(e), "prefill": {"title": title, "kind": kind, "json": raw}},
                )

        tpl = DesignTemplate.objects.create(title=title, kind=kind, json_active=data)
        DesignTemplateVersion.objects.create(
            template=tpl, version=1, json_payload=data, created_by=request.user, note="Versión inicial"
        )
        return redirect("administracion:plantilla_edit", tpl_id=tpl.id)

    return render(
    request,
    "administracion/plantilla_form.html",
    {
        "mode": "create",
        "prefill": {},
        # dict funciona con lookup por punto en Django templates
        "item": {"title": "", "kind": DesignTemplate.DESIGN, "json": ""},
    },
)

@login_required
@csp_update({
    'script-src': ("'self'", csp.NONCE),
    'style-src': ("'self'", "https://fonts.googleapis.com", csp.NONCE),
    'img-src': ("'self'", "data:", "blob:"),
})
@csp_update({'script-src': ("'self'", csp.NONCE, "https://cdn.jsdelivr.net")})
def plantilla_edit(request, tpl_id: int):
    tpl = get_object_or_404(DesignTemplate, pk=tpl_id)
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest("Cuerpo inválido")
        tpl.json_active = data
        tpl.save(update_fields=["json_active", "updated_at"])
        return JsonResponse({"ok": True})

    assets = TemplateAsset.objects.all().order_by("-created_at")[:200]
    return render(
        request,
        "administracion/plantilla_editor.html",
        {"tpl": tpl, "assets": assets, "csrf_token": get_token(request)}
    )

@login_required
@require_http_methods(["POST"])
def plantilla_duplicate(request, tpl_id: int):
    tpl = get_object_or_404(DesignTemplate, pk=tpl_id)
    clone = DesignTemplate.objects.create(
        title=f"{tpl.title} (copia)",
        kind=tpl.kind,
        json_active=tpl.json_active,
        org=tpl.org
    )
    DesignTemplateVersion.objects.create(
        template=clone, version=1, json_payload=tpl.json_active, created_by=request.user, note="Copia"
    )
    return redirect("administracion:plantilla_edit", tpl_id=clone.id)

@login_required
@require_http_methods(["POST"])
def plantilla_new_version(request, tpl_id: int):
    tpl = get_object_or_404(DesignTemplate, pk=tpl_id)
    payload = request.POST.get("json")
    if not payload:
        return HttpResponseBadRequest("Falta json")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("JSON inválido")

    last = DesignTemplateVersion.objects.filter(template=tpl).aggregate(m=Max("version")).get("m") or 0
    v = last + 1
    DesignTemplateVersion.objects.create(
        template=tpl, version=v, json_payload=data, created_by=request.user, note=request.POST.get("note", ""))
    tpl.json_active = data
    tpl.save(update_fields=["json_active", "updated_at"])
    return redirect("administracion:plantilla_edit", tpl_id=tpl.id)

@login_required
def assets_library(request):
    items = TemplateAsset.objects.all().order_by("-created_at")
    return render(request, "administracion/assets_library.html", {"items": items})

@login_required
@require_http_methods(["POST"])
def asset_upload(request):
    f = request.FILES.get("file")
    if not f:
        return HttpResponseBadRequest("Falta archivo")
    asset = TemplateAsset.objects.create(name=f.name, file=f, mime=f.content_type or "")
    return JsonResponse({"ok": True, "id": asset.id, "name": asset.name, "url": asset.file.url})

@login_required
@require_http_methods(["POST"])
def asset_delete(request, pk: int):
    """Elimina un asset y, si existe, el archivo físico en disco."""
    asset = get_object_or_404(TemplateAsset, pk=pk)
    file_path = None
    if asset.file and hasattr(asset.file, "path"):
        file_path = asset.file.path
    asset.delete()
    if file_path:
        try:
            os.remove(file_path)
        except Exception:
            pass
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("administracion:assets_library")


# ========== PROGRAMAS / DIPLOMADOS ==========

@login_required
def program_list(request):
    q = request.GET.get("q", "").strip() or None
    items = fetch_programs(q)
    return render(request, "administracion/program_list.html", {"items": items, "q": q or ""})

@login_required
@require_http_methods(["GET", "POST"])
def program_create(request):
    if request.method == "POST":
        name = request.POST.get("name")
        code = request.POST.get("code")
        ctype = request.POST.get("constancia_type") or ConstanciaType.CEPROEM
        plantilla_d = request.POST.get("plantilla_diploma") or None
        plantilla_c = request.POST.get("plantilla_constancia") or None

        ProgramAdmin.objects.create(
            name=name,
            code=code,
            constancia_type=ctype,
            plantilla_diploma=DesignTemplate.objects.filter(id=plantilla_d).first() if plantilla_d else None,
            plantilla_constancia=DesignTemplate.objects.filter(id=plantilla_c).first() if plantilla_c else None,
        )
        return redirect("administracion:program_list")

    plantillas = DesignTemplate.objects.all().order_by("title")
    return render(
        request,
        "administracion/program_form.html",
        {"mode": "create", "plantillas": plantillas, "ConstanciaType": ConstanciaType},
    )

@login_required
@require_http_methods(["GET", "POST"])
def program_edit(request, pk: int):
    p = get_object_or_404(ProgramAdmin, pk=pk)
    if request.method == "POST":
        p.name = request.POST.get("name") or p.name
        p.code = request.POST.get("code") or p.code
        p.constancia_type = request.POST.get("constancia_type") or p.constancia_type
        plantilla_d = request.POST.get("plantilla_diploma") or None
        plantilla_c = request.POST.get("plantilla_constancia") or None
        p.plantilla_diploma = DesignTemplate.objects.filter(id=plantilla_d).first() if plantilla_d else None
        p.plantilla_constancia = DesignTemplate.objects.filter(id=plantilla_c).first() if plantilla_c else None
        p.save()
        return redirect("administracion:program_list")

    plantillas = DesignTemplate.objects.all().order_by("title")
    return render(
        request,
        "administracion/program_form.html",
        {"mode": "edit", "item": p, "plantillas": plantillas, "ConstanciaType": ConstanciaType},
    )

@require_http_methods(["POST"])
def program_delete(request, source: str, pk: int):
    """
    Elimina por origen:
      - 'sim' -> DELETE FROM ces_simulacion.diplomado
      - 'app' -> DELETE FROM ces_db.alumnos_program
    Muestra mensajes de éxito/error y redirige a la lista.
    """
    try:
        if source == "sim":
            with transaction.atomic(using="ces"):
                _query_simulacion("DELETE FROM diplomado WHERE id = %s", [pk])
            messages.success(request, f"Diplomado (sim) #{pk} eliminado.")
        elif source == "app":
            with transaction.atomic(using="default"):
                _query_default("DELETE FROM alumnos_program WHERE id = %s", [pk])
            messages.success(request, f"Programa (app) #{pk} eliminado.")
        else:
            messages.error(request, "Origen inválido.")
    except Exception as e:
        messages.error(request, f"No se pudo eliminar: {escape(str(e))}")

    return redirect(reverse("administracion:program_list"))
@login_required
@require_http_methods(["POST"])
def plantilla_upload_thumb(request, tpl_id: int):
    """
    Sube una imagen manual y la guarda en DesignTemplate.thumb.
    No toca json_active ni el flujo de edición.
    """
    tpl = get_object_or_404(DesignTemplate, pk=tpl_id)
    f = request.FILES.get("thumb")
    if not f:
        return JsonResponse({"ok": False, "msg": "Falta archivo (thumb)."}, status=400)
    tpl.thumb = f
    tpl.save(update_fields=["thumb", "updated_at"])
    return JsonResponse({"ok": True, "url": tpl.thumb.url})

@login_required
@require_http_methods(["POST"])
def plantilla_regen_thumb(request, tpl_id: int):
    """
    Regenera la miniatura desde json_active y la guarda en thumb.
    Fuerza override para garantizar actualización.
    """
    tpl = get_object_or_404(DesignTemplate, pk=tpl_id)
    ok = save_thumb(tpl, force=True)
    if ok:
        tpl.save(update_fields=["thumb", "updated_at"])
        return JsonResponse({"ok": True, "url": tpl.thumb.url if tpl.thumb else None})
    return JsonResponse({"ok": False, "msg": "No se pudo generar la miniatura."}, status=500)

@login_required
@require_http_methods(["POST"])
def plantilla_delete(request, tpl_id: int):
    tpl = get_object_or_404(DesignTemplate, pk=tpl_id)
    title = tpl.title
    tpl.delete()
    messages.success(request, f'Plantilla «{title}» eliminada.')
    return redirect("administracion:plantillas_admin")

@login_required
@require_http_methods(["POST"])
def plantilla_import(request):
    """
    Importa un documento (imagen/PDF/Office) **sin convertir**.
    Guarda el archivo como TemplateAsset y crea una plantilla vacía.
    Luego, desde el editor podrás 'Convertir a imagen' si lo deseas.
    """
    f = request.FILES.get("file")
    if not f:
        messages.error(request, "No se recibió ningún archivo.")
        return redirect("administracion:plantillas_admin")

    name = Path(f.name).name
    ext  = Path(f.name).suffix.lower()

    # 1) Guardar SIEMPRE el archivo original como asset
    asset = TemplateAsset.objects.create(name=name, file=f, mime=f.content_type or "")

    # 2) Crear una plantilla mínima (página en blanco)
    data = {
        "pages": [{
            "width": 1920, "height": 1080, "background": "#ffffff",
            "layers": [
                # Podríamos colocar una nota de texto como guía:
                {"type":"text","text":f"Adjunto: {name}", "x":64, "y":64, "fontSize":36, "fill":"#111"}
            ]
        }]
    }
    tpl = DesignTemplate.objects.create(title=name, kind=DesignTemplate.DESIGN, json_active=data)

    # 3) Aviso + sugerencia
    messages.success(
        request,
        f"Se adjuntó «{name}». El archivo original se conservó sin cambios. "
        "Desde el editor puedes usar 'Convertir a imagen' si necesitas usarlo como fondo."
    )
    return redirect("administracion:plantilla_edit", tpl_id=tpl.id)


def _pdf_to_png_bytes(pdf_bytes: bytes):
    """PDF -> PNG (1ª página) usando pdf2image + Poppler."""
    try:
        from pdf2image import convert_from_bytes
        imgs = convert_from_bytes(pdf_bytes, dpi=150, poppler_path=POPPLER_BIN or None)
        if not imgs:
            return None
        img0 = imgs[0]
        if img0.mode != "RGB":
            img0 = img0.convert("RGB")
        buf = io.BytesIO()
        img0.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None

def _office_to_pdf_bytes(uploaded_file, name_hint: str):
    """DOC/DOCX/PPT/PPTX/ODT/ODP -> PDF con LibreOffice (headless)."""
    soffice = _find_soffice()
    if not soffice:
        return None
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / name_hint
        with open(src, "wb") as out:
            for ch in uploaded_file.chunks():
                out.write(ch)
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", td, str(src)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            return None
        pdf_path = src.with_suffix(".pdf")
        if not pdf_path.exists():
            cand = list(Path(td).glob("*.pdf"))
            pdf_path = cand[0] if cand else None
        return pdf_path.read_bytes() if pdf_path and pdf_path.exists() else None
# ============= NUEVA VISTA =============
@login_required
@require_http_methods(["POST"])
def import_office_to_image(request):
    """
    Endpoint AJAX: recibe 'file', convierte a imagen (1a página),
    crea una DesignTemplate con esa imagen como fondo y responde JSON.
    """
    up = request.FILES.get("file")
    if not up:
        return JsonResponse({"ok": False, "error": "Falta archivo."}, status=400)

    name = Path(up.name).name
    ext  = Path(up.name).suffix.lower()

    png_bytes = None
    if ext == ".pdf":
        pdf_bytes = b"".join(up.chunks())
        png_bytes = _pdf_to_png_bytes(pdf_bytes)
    elif ext in {".doc", ".docx", ".ppt", ".pptx", ".odt", ".odp"}:
        pdf_bytes = _office_to_pdf_bytes(up, name)
        if pdf_bytes:
            png_bytes = _pdf_to_png_bytes(pdf_bytes)
    elif ext in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        # si es imagen, simplemente la guardamos
        from .models import TemplateAsset, DesignTemplate
        asset = TemplateAsset.objects.create(name=name, file=up, mime=up.content_type or "")
        data = {
            "pages": [{
                "width": 1920, "height": 1080, "background": "#ffffff",
                "layers": [{"type":"image","url":asset.file.url,"x":0,"y":0,"w":1920,"h":1080}]
            }]
        }
        tpl = DesignTemplate.objects.create(title=name, kind=DesignTemplate.DESIGN, json_active=data)
        return JsonResponse({"ok": True, "template_id": tpl.id, "redirect": reverse("administracion:plantilla_edit", args=[tpl.id])})

    if not png_bytes:
        return JsonResponse({
            "ok": False,
            "error": "No se pudo convertir el documento. Instala Poppler (pdf2image) y LibreOffice para Office."
        }, status=501)

    # guardar PNG como asset y crear plantilla
    from .models import TemplateAsset, DesignTemplate
    img_name = Path(name).with_suffix(".png").name
    asset = TemplateAsset.objects.create(
        name=img_name,
        file=ContentFile(png_bytes, name=img_name),
        mime="image/png",
    )
    data = {
        "pages": [{
            "width": 1920, "height": 1080, "background": "#ffffff",
            "layers": [{"type":"image","url":asset.file.url,"x":0,"y":0,"w":1920,"h":1080}]
        }]
    }
    tpl = DesignTemplate.objects.create(title=name, kind=DesignTemplate.DESIGN, json_active=data)
    return JsonResponse({"ok": True, "template_id": tpl.id, "redirect": reverse("administracion:plantilla_edit", args=[tpl.id])})

def _find_soffice():
    # Si definiste SOFFICE_BIN, úsalo
    if SOFFICE_BIN and Path(SOFFICE_BIN).exists():
        return SOFFICE_BIN
    # Rutas típicas en Windows
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "soffice",  # si está en PATH
    ]
    for c in candidates:
        p = Path(c)
        if (p.exists() and p.is_file()) or c == "soffice":
            return c
    return None

@login_required
@require_http_methods(["POST"])
def asset_convert_to_image(request, asset_id: int):
    """
    Convierte un asset (PDF/Office/imagen) a PNG (1ª página) y devuelve la URL del nuevo asset PNG.
    No borra el original.
    """
    asset = get_object_or_404(TemplateAsset, pk=asset_id)
    name = Path(asset.name).name
    ext  = Path(asset.name).suffix.lower()

    png_bytes = None
    if ext == ".pdf":
        # leer bytes del archivo original
        with asset.file.open("rb") as fh:
            pdf_bytes = fh.read()
        png_bytes = _pdf_to_png_bytes(pdf_bytes)
    elif ext in {".doc", ".docx", ".ppt", ".pptx", ".odt", ".odp"}:
        with asset.file.open("rb") as fh:
            # fake UploadedFile para reuse de helper
            class _U:
                def __init__(self, b): self._b = b
                def chunks(self, csize=64*1024):
                    yield self._b
            pdf_bytes = _office_to_pdf_bytes(_U(fh.read()), name)
        if pdf_bytes:
            png_bytes = _pdf_to_png_bytes(pdf_bytes)
    elif ext in {".png", ".jpg", ".jpeg", ".webp"}:
        with asset.file.open("rb") as fh:
            png_bytes = fh.read() if ext == ".png" else None  # ya es imagen (si jpg/webp podrías convertir)
        if not png_bytes:
            try:
                from PIL import Image
                im = Image.open(asset.file)
                if im.mode != "RGB": im = im.convert("RGB")
                buff = io.BytesIO()
                im.save(buff, format="PNG")
                png_bytes = buff.getvalue()
            except Exception:
                png_bytes = None
    else:
        return JsonResponse({"ok": False, "error": "Formato no soportado para convertir."}, status=400)

    if not png_bytes:
        return JsonResponse({
            "ok": False,
            "error": "No se pudo convertir. Revisa Poppler (pdf2image) y, si es Office, LibreOffice (soffice)."
        }, status=501)

    # Guardar nuevo asset PNG
    img_name = Path(name).with_suffix(".png").name
    new_asset = TemplateAsset.objects.create(
        name=img_name,
        file=ContentFile(png_bytes, name=img_name),
        mime="image/png",
    )
    return JsonResponse({"ok": True, "id": new_asset.id, "name": new_asset.name, "url": new_asset.file.url})
def _build_abs_media_url(request, rel_path):
    """Devuelve URL absoluta pública a un archivo en MEDIA_ROOT."""
    return request.build_absolute_uri(settings.MEDIA_URL + rel_path.replace("\\", "/"))
@login_required
@require_POST
def plantilla_import_convert(request):
    """
    Recibe un archivo Office y lo convierte a PDF con LibreOffice headless.
    Respuesta JSON:
      { "pdf_url": "https://.../media/office_conv/<id>/file.pdf" }
    """
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "file requerido"}, status=400)

    # Carpeta destino dentro de MEDIA_ROOT (p.ej. media/office_conv/<uuid>/)
    conv_root = Path(settings.MEDIA_ROOT) / "office_conv" / uuid.uuid4().hex
    conv_root.mkdir(parents=True, exist_ok=True)

    src_name = f.name
    src_path = conv_root / src_name
    with open(src_path, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)

    # Comando LibreOffice (headless)
    soffice = getattr(settings, "LIBREOFFICE_PATH", "soffice")

    try:
        # Convertir a PDF en la misma carpeta
        # --headless: sin UI
        # --convert-to pdf: salida pdf
        # --outdir <dir>: carpeta de salida
        proc = subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(conv_root), str(src_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120
        )
        if proc.returncode != 0:
            # Si LibreOffice no está instalado / no en PATH, devuelve 501
            return JsonResponse(
                {"error": "LibreOffice no disponible", "stderr": proc.stderr},
                status=501
            )
    except FileNotFoundError:
        return JsonResponse({"error": "LibreOffice no encontrado"}, status=501)
    except subprocess.TimeoutExpired:
        return JsonResponse({"error": "Tiempo de conversión excedido"}, status=504)

    # Nombre del PDF generado (mismo nombre base, .pdf)
    pdf_name = Path(src_name).with_suffix(".pdf").name
    pdf_path = conv_root / pdf_name
    if not pdf_path.exists():
        return JsonResponse({"error": "Conversión fallida"}, status=500)

    # Ruta relativa para componer URL
    rel = str(pdf_path.relative_to(settings.MEDIA_ROOT))
    return JsonResponse({"pdf_url": _build_abs_media_url(request, rel)})
def _encrypt_with_permissions(working_pdf: bytes, *, allow_print_lowres=False) -> bytes:
    with pikepdf.open(io.BytesIO(working_pdf)) as pdf:
        # 1) limpiar metadatos (opcional pero recomendable)
        try:
            pdf.docinfo.clear()
            if "/Metadata" in pdf.root:
                del pdf.root["/Metadata"]
        except Exception:
            pass

        # 2) permisos: abrir sin password pero pedir owner p/editar
        desired = {
            "print_lowres": allow_print_lowres,  # True si quieres permitir impresión baja
            "print_highres": False,
            "extract": False,
            "modify": False,
            "annotate": False,
            "form": False,
            "assemble": False,
            "accessibility": False,
        }
        perm_params = set(inspect.signature(pikepdf.Permissions).parameters.keys())
        filtered = {k: v for k, v in desired.items() if k in perm_params}
        perms = pikepdf.Permissions(**filtered)

        enc = pikepdf.Encryption(
            user="",                         # <-- SIN contraseña de apertura
            owner=secrets.token_hex(16),     # <-- contraseña de permisos (NO la compartas)
            R=6,                             # AES-256
            allow=perms
        )

        out = io.BytesIO()
        pdf.save(out, encryption=enc, linearize=False)
        return out.getvalue()

@require_POST
@login_required
@csrf_protect
def program_bulk_delete(request):
    # Espera JSON: { "ids": [1,2,3,...] }
    import json
    try:
        data = json.loads(request.body.decode("utf-8"))
        ids = data.get("ids", [])
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    if not isinstance(ids, list):
        return JsonResponse({"ok": False, "error": "ids debe ser una lista."}, status=400)

    # Autorización adicional si aplica…
    Program.objects.filter(id__in=ids).delete()
    return JsonResponse({"ok": True, "deleted": len(ids)})

def _query_simulacion(sql, params=None):
    with connections['ces'].cursor() as cur:
        cur.execute(sql, params or [])
        # Si es SELECT habrá description; si no, es escritura.
        if cur.description:
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        return cur.rowcount  # para DELETE/UPDATE/INSERT

def _query_default(sql, params=None):
    with connections['default'].cursor() as cur:
        cur.execute(sql, params or [])
        if cur.description:
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        return cur.rowcount

@require_http_methods(["POST"])
def program_delete(request, source: str, pk: int):
    try:
        if source == "sim":
            with transaction.atomic(using="ces"):
                _query_simulacion("DELETE FROM diplomado WHERE id = %s", [pk])
            messages.success(request, f"Diplomado (sim) #{pk} eliminado.")
        elif source == "app":
            with transaction.atomic(using="default"):
                _query_default("DELETE FROM alumnos_program WHERE id = %s", [pk])
            messages.success(request, f"Programa (app) #{pk} eliminado.")
        else:
            messages.error(request, "Origen inválido.")
    except Exception as e:
        messages.error(request, f"No se pudo eliminar: {escape(str(e))}")
    return redirect(reverse("administracion:program_list"))

# ---------- LÓGICA DE NEGOCIO ----------
def fetch_programs(search_text=None):
    """
    Une programas de:
      - ces_simulacion.diplomado
      - ces_db.alumnos_program
    Estandariza campos con alias: codigo, nombre, modalidad, fuente.
    """
    like = f"%{search_text}%" if search_text else None

    # OJO: usa la PK real de cada tabla y dale alias AS codigo
    # Ajusta los nombres 'nombre' y 'modalidad' si en tu esquema se llaman distinto
    sql_sim = """
        SELECT
            d.id            AS codigo,     -- si tu PK es otra (p.ej. id_diplomado/clave), cámbiala aquí
            d.nombre        AS nombre,     -- cámbialo si tu columna es 'titulo' u otro
            d.modalidad     AS modalidad,  -- si no existe, puedes devolver NULL
            'simulacion'    AS fuente
        FROM diplomado d
        WHERE (%s IS NULL OR d.nombre LIKE %s)
        ORDER BY d.id DESC
    """
    sim_params = [like, like]

    sql_def = """
        SELECT
            p.id            AS codigo,     -- si tu tabla tiene 'codigo' úsala; si no, deja 'id'
            p.nombre        AS nombre,
            p.modalidad     AS modalidad,
            'alumnos_program' AS fuente
        FROM alumnos_program p
        WHERE (%s IS NULL OR p.nombre LIKE %s)
        ORDER BY p.id DESC
    """
    def_params = [like, like]

    sim_rows = _query_simulacion(sql_sim, sim_params)
    def_rows = _query_default(sql_def, def_params)

    # Unimos resultados
    items = sim_rows + def_rows
    return items
def _table_columns(using_alias: str, schema: str, table: str) -> set[str]:
    """
    Devuelve el conjunto de columnas existentes para schema.table en la conexión 'using_alias'.
    using_alias típicos: 'ces' (ces_simulacion), 'default' (ces_db).
    """
    with connections[using_alias].cursor() as cur:
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
            """,
            [schema, table],
        )
        return {row[0] for row in cur.fetchall()}

def _pick(cols: set[str], candidates: list[str]) -> str | None:
    """Devuelve el primer nombre de columna candidato que exista en 'cols'."""
    for c in candidates:
        if c in cols:
            return c
    return None

def _safe_like(q: str | None) -> str | None:
    return f"%{q.strip()}%" if q else None

def _build_select(schema: str, table: str, alias: str, cols: set[str], fuente: str, q: str | None):
    """
    Construye un SELECT que normaliza:
      - codigo (PK o ‘clave’)
      - nombre  (título del programa)
      - modalidad (si existe; si no, NULL)
      - fuente  (constante para saber de dónde viene)
    Retorna: (sql, params) o (None, None) si no hay al menos codigo+nombre.
    """
    # Posibles nombres en tus tablas
    code_opts      = ["codigo", "clave", "cod", "cve", "id_diplomado", "id", "clave_diplomado", "codigo_prog", "cod_programa"]
    name_opts      = ["nombre", "nombre_diplomado", "nom_diplomado", "programa", "titulo", "descripcion", "nombre_programa", "name"]
    modality_opts  = ["modalidad", "modalidad_nombre", "tipo", "tipo_modalidad", "modalidad_prog"]

    col_code = _pick(cols, code_opts)
    col_name = _pick(cols, name_opts)
    col_mod  = _pick(cols, modality_opts)  # puede no existir

    if not col_code or not col_name:
        return None, None

    select_parts = [
        f"{alias}.`{col_code}` AS codigo",
        f"{alias}.`{col_name}` AS nombre",
        f"{alias}.`{col_mod}` AS modalidad" if col_mod else "NULL AS modalidad",
        "%s AS fuente",
    ]

    where_parts = []
    params = [fuente]

    like_q = _safe_like(q)
    if like_q:
        # filtra por nombre o por código textual si aplica
        where_parts.append(f"({alias}.`{col_name}` LIKE %s OR CAST({alias}.`{col_code}` AS CHAR) LIKE %s)")
        params.extend([like_q, like_q])

    sql = f"SELECT {', '.join(select_parts)} FROM `{schema}`.`{table}` {alias}"
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)

    return sql, params

def _query_dicts(using_alias: str, sql: str, params: list) -> list[dict]:
    """Ejecuta y devuelve lista de dicts con nombres de columna."""
    with connections[using_alias].cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in rows]

def fetch_programs(search_text: str | None = None) -> list[dict]:
    """
    Une programas desde:
      - ces_simulacion.diplomado  (conexión 'ces')     → fuente = 'simulacion'
      - ces_db.alumnos_program     (conexión 'default')→ fuente = 'alumnos_program'
    Descubre columnas reales y normaliza a: codigo, nombre, modalidad, fuente.
    """
    items: list[dict] = []

    # ---------- SIMULACION ----------
    try:
        ces_schema = settings.DATABASES["ces"]["NAME"]      # usualmente 'ces_simulacion'
    except Exception:
        ces_schema = "ces_simulacion"
    sim_table  = "diplomado"
    sim_cols   = _table_columns("ces", ces_schema, sim_table)

    sim_sql, sim_params = _build_select(
        schema=ces_schema, table=sim_table, alias="d",
        cols=sim_cols, fuente="simulacion", q=search_text
    )
    if sim_sql:
        try:
            items.extend(_query_dicts("ces", sim_sql, sim_params))
        except Exception:
            # si falla esta fuente, seguimos con la otra
            pass

    # ---------- APP (DEFAULT) ----------
    try:
        def_schema = settings.DATABASES["default"]["NAME"]  # usualmente 'ces_db'
    except Exception:
        def_schema = "ces_db"
    app_table = "alumnos_program"
    app_cols  = _table_columns("default", def_schema, app_table)

    app_sql, app_params = _build_select(
        schema=def_schema, table=app_table, alias="p",
        cols=app_cols, fuente="alumnos_program", q=search_text
    )
    if app_sql:
        try:
            items.extend(_query_dicts("default", app_sql, app_params))
        except Exception:
            pass

    # Ordena por nombre y luego por código para vista estable
    items.sort(key=lambda x: ((x.get("nombre") or "").lower(), str(x.get("codigo") or "")))
    return items