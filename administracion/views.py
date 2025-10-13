# administracion/views.py
from datetime import timedelta
import requests

from django.conf import settings
from django.contrib.auth import (
    authenticate, login, logout, get_user_model, update_session_auth_hash
)
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, FormView
from django.middleware.csrf import get_token
from django_otp.decorators import otp_required

from alumnos.models import Request, Program, RequestEvent
from .models import Graduate, AdminAccessLog
from .forms import AdminLoginForm
from .security import failed_attempts_count

User = get_user_model()


# ====================== Helpers de autorización ======================

def _in_admin_group(user) -> bool:
    try:
        return user.groups.filter(name="AdministradoresCES").exists()
    except Exception:
        return False

def _admin_allowed(user) -> bool:
    """
    Permite:
      - superuser (si existe el campo)
      - staff (si existe el campo)
      - grupo 'AdministradoresCES'
    """
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

        # métricas (globales)
        ctx["total_requests"] = Request.objects.count()
        ctx["pending"] = Request.objects.filter(status="pending").count()
        ctx["accepted"] = Request.objects.filter(status="accepted").count()
        ctx["rejected"] = Request.objects.filter(status="rejected").count()
        ctx["total_graduates"] = Graduate.objects.count()

        # búsqueda
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

        # tabla principal
        ctx["recent_requests"] = qs[:20]

        # seguridad
        ctx["recent_logs"] = AdminAccessLog.objects.select_related("user").order_by("-created_at")[:12]
        ctx["now"] = timezone.now()

        # grupos del usuario (tolerante si la tabla M2M aún no existe)
        try:
            ctx["user_groups"] = list(self.request.user.groups.values_list("name", flat=True))
        except Exception:
            ctx["user_groups"] = None

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

        # Mensaje genérico para evitar enumeración
        if not auth_user or not auth_user.is_active:
            form.add_error(None, "Credenciales inválidas.")
            return self.form_invalid(form)

        if not _admin_allowed(auth_user):
            form.add_error(None, "Credenciales inválidas.")
            return self.form_invalid(form)

        login(self.request, auth_user)

        # Política de sesión
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


# =========================== Endpoints AJAX ===========================

@require_POST
def password_change_inline(request):
    """
    Cambia la contraseña del usuario actual (desde el modal).
    Mantiene la sesión activa con update_session_auth_hash.
    Responde JSON: {ok: True} o {ok: False, error: "..."}
    """
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
    update_session_auth_hash(request, user)  # mantiene la sesión
    return JsonResponse({"ok": True})


@require_POST
def create_admin_inline(request):
    """
    Crea un nuevo usuario administrador.
    Marca is_staff si el modelo lo soporta y/o lo agrega al grupo AdministradoresCES.
    """
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

    # Sugerir username si no llega
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

    # Marcar staff si el campo existe
    if hasattr(u, "is_staff"):
        u.is_staff = True
        u.save(update_fields=["is_staff"])

    # Agregar al grupo si existe (crea si no)
    grp, _ = Group.objects.get_or_create(name="AdministradoresCES")
    u.groups.add(grp)

    return JsonResponse({"ok": True, "user": {"id": u.id, "username": u.username, "email": u.email}})


# ================== Tablero de solicitudes y estado ==================

class RequestsBoardView(LoginRequiredMixin, TemplateView):
    """
    Tablero con solicitudes agrupadas por programa + filtros.
    """
    template_name = "administracion/solicitudes.html"
    login_url = "administracion:login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        program_id = (self.request.GET.get("program") or "").strip()

        # Base queryset
        qs = Request.objects.select_related("program").order_by("-sent_at")
        if q:
            qs = qs.filter(
                Q(email__icontains=q) |
                Q(name__icontains=q) |
                Q(lastname__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if program_id:
            qs = qs.filter(program_id=program_id)

        # Programas y agrupación manual
        programas = Program.objects.all().order_by("name")
        bucket = {p.id: [] for p in programas}
        bucket_none = []
        for s in qs:
            if getattr(s, "program_id", None) in bucket:
                bucket[s.program_id].append(s)
            else:
                bucket_none.append(s)

        por_programa = [{"program": p, "items": bucket[p.id]} for p in programas]
        if bucket_none:
            por_programa.append({"program": None, "items": bucket_none})

        # Estados (valor, etiqueta)
        statuses = [
            ("pending", "Pendiente"),
            ("review", "Revisión"),
            ("accepted", "Aprobada"),
            ("rejected", "Rechazada"),
            ("generating", "Generando"),
        ]

        counts = qs.values("status").annotate(total=Count("id"))
        ctx.update({
            "q": q,
            "status": status,
            "program_id": program_id,
            "programas": programas,
            "por_programa": por_programa,
            "counts": {c["status"]: c["total"] for c in counts},
            "statuses": statuses,
            "now": timezone.now(),
        })

        # ➜ CSRF token para el fetch en la plantilla
        ctx["csrf_token"] = get_token(self.request)

        return ctx


def _log_event_only_once(req_obj: Request, status: str, note: str = ""):
    """Crea un RequestEvent solo la primera vez que la solicitud entra a ese estado."""
    if not RequestEvent.objects.filter(request=req_obj, status=status).exists():
        RequestEvent.objects.create(request=req_obj, status=status, note=(note or None))


@require_POST
def request_update_status(request):
    """
    Actualiza el estado de una solicitud y registra un evento (solo primera vez).
      - to_review  -> review
      - approve    -> accepted
      - reject     -> rejected  (requiere 'reason')
      - generating -> generating
    """
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

    # Validación de rechazo
    if new_status == "rejected" and not reason:
        return JsonResponse({"ok": False, "msg": "Falta el motivo de rechazo."}, status=400)

    # Persistencia del estado + motivo (si aplica)
    if new_status == "rejected":
        req_obj.status_reason = reason
        req_obj.status = new_status
        req_obj.save(update_fields=["status", "status_reason"])
    else:
        req_obj.status = new_status
        req_obj.save(update_fields=["status"])

    # Registrar evento la primera vez que se entra al estado
    _log_event_only_once(req_obj, new_status, reason)

    return JsonResponse({"ok": True, "new_status": new_status})
