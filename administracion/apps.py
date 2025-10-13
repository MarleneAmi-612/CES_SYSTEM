from django.apps import AppConfig


def _get_client_ip(request):
    """
    Extrae IP real respetando proxies (X-Forwarded-For).
    """
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AdministracionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "administracion"

    def ready(self):
        # Señales de login/logout
        from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed as dj_user_login_failed
        from django.dispatch import receiver

        # Intentamos usar la señal de Axes si está instalada; si no, usamos la de Django
        try:
            from axes.signals import user_login_failed as axes_user_login_failed
            login_failed_signal = axes_user_login_failed  # Axes bloqueará/registrará también
            reason = "axes_failed"
        except Exception:
            login_failed_signal = dj_user_login_failed
            reason = "auth_failed"

        from .models import AdminAccessLog

        @receiver(user_logged_in)
        def _on_login(sender, request, user, **kwargs):
            AdminAccessLog.objects.create(
                user=user,
                username=user.get_username(),
                ip=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                session_key=getattr(getattr(request, "session", None), "session_key", "") or "",
                event=AdminAccessLog.EVENT_LOGIN_SUCCESS,
                extra={}
            )

        @receiver(user_logged_out)
        def _on_logout(sender, request, user, **kwargs):
            AdminAccessLog.objects.create(
                user=user if getattr(user, "is_authenticated", False) else None,
                username=getattr(user, "username", "") or "",
                ip=_get_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else ""),
                session_key=(getattr(getattr(request, "session", None), "session_key", "") if request else ""),
                event=AdminAccessLog.EVENT_LOGOUT,
                extra={}
            )

        @receiver(login_failed_signal)
        def _on_login_failed(sender, credentials=None, request=None, **kwargs):
            username = ""
            if isinstance(credentials, dict):
                username = credentials.get("username") or credentials.get("email") or ""
            AdminAccessLog.objects.create(
                user=None,
                username=username,
                ip=_get_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else ""),
                session_key=(getattr(getattr(request, "session", None), "session_key", "") if request else ""),
                event=AdminAccessLog.EVENT_LOGIN_FAILURE,
                extra={"reason": reason}
            )
