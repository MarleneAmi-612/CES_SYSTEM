# alumnos/middleware.py
from datetime import timedelta

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class AlumnosSessionGuard:
    """
    Protege TODAS las rutas /alumnos/*, excepto:
      - /alumnos/          (start)
      - /alumnos/estatus/  (status)   -> públicas

    /alumnos/api/tracking/<id>/ es pública (la usa el polling del tracking).

    /alumnos/seguimiento/<id>/ es accesible si:
      - hay sesión de flujo (alumno_email/basic/extras) O
      - existe un pase temporal 'tracking_ok' emitido desde /estatus/ (<= 15 min)
    En cualquier otro caso redirige a alumnos:start.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._public_exact = None

    def __call__(self, request):
        if self._public_exact is None:
            self._public_exact = {
                reverse("alumnos:start"),
                reverse("alumnos:status"),
            }

        path = request.path

        # Fuera de /alumnos → permitir
        if not path.startswith("/alumnos/"):
            return self.get_response(request)

        # ✅ API pública del tracking (para el polling)
        if path.startswith("/alumnos/api/tracking/"):
            return self.get_response(request)

        # Rutas públicas exactas
        if path in self._public_exact:
            return self.get_response(request)

        # ¿flujo activo?
        flow_ok = any(k in request.session for k in ("alumno_email", "basic", "extras"))

        # ¿está intentando ver seguimiento?
        is_tracking = path.startswith("/alumnos/seguimiento/")
        if is_tracking and not flow_ok:
            # pase temporal desde /estatus/
            tracking_ok = bool(request.session.get("tracking_ok"))
            if tracking_ok:
                issued = request.session.get("tracking_issued_at")
                try:
                    issued_dt = timezone.datetime.fromisoformat(issued)
                    if timezone.is_naive(issued_dt):
                        issued_dt = timezone.make_aware(issued_dt, timezone.get_current_timezone())
                except Exception:
                    issued_dt = None

                if issued_dt and timezone.now() - issued_dt <= timedelta(minutes=15):
                    # pase válido -> permitir
                    return self.get_response(request)

        # Si no hay flujo ni pase válido, redirige a start
        if not flow_ok and not (is_tracking and request.session.get("tracking_ok")):
            return redirect(reverse("alumnos:start"))

        return self.get_response(request)
