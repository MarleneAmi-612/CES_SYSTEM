# administracion/security.py
from datetime import timedelta
from django.utils import timezone
from axes.models import AccessAttempt

def failed_attempts_count(request, username_or_email=None, window_minutes=60):
    """
    Cuenta intentos fallidos recientes de login para mostrar avisos/bloqueos.
    Compatible con django-axes (campos: attempt_time, failures_since_start, ip_address, username).
    """
    since = timezone.now() - timedelta(minutes=window_minutes)

    qs = AccessAttempt.objects.filter(
        failures_since_start__gt=0,
        attempt_time__gte=since,      # << antes usabas last_attempt_time__gte
    )

    if username_or_email:
        qs = qs.filter(username=username_or_email)

    # opcional: acotar por IP del cliente
    ip = request.META.get("REMOTE_ADDR")
    if ip:
        qs = qs.filter(ip_address=ip)

    return qs.count()
