# administracion/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .models import AdminAccessLog
from .utils import get_client_ip

@receiver(user_logged_in)
def log_login_success(sender, request, user, **kwargs):
    AdminAccessLog.objects.create(
        event=AdminAccessLog.Event.LOGIN_SUCCESS,
        user=user,
        username=user.get_username(),
        ip=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT",""),
        session_key=getattr(request.session, "session_key", "") or "",
        extra={}
    )

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    AdminAccessLog.objects.create(
        event=AdminAccessLog.Event.LOGOUT,
        user=user if user and user.is_authenticated else None,
        username=(user.get_username() if user and hasattr(user, "get_username") else ""),
        ip=get_client_ip(request) if request else "",
        user_agent=request.META.get("HTTP_USER_AGENT","") if request else "",
        session_key=(getattr(request.session, "session_key", "") if request else ""),
        extra={}
    )

@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    username = (credentials or {}).get("username") or (credentials or {}).get("email") or ""
    AdminAccessLog.objects.create(
        event=AdminAccessLog.Event.LOGIN_FAILURE,
        user=None,
        username=username,
        ip=get_client_ip(request) if request else "",
        user_agent=request.META.get("HTTP_USER_AGENT","") if request else "",
        session_key=(getattr(request.session, "session_key", "") if request else ""),
        extra={"reason": "auth_failed"}
    )
