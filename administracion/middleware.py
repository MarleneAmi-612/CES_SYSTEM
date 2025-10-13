from django.http import HttpResponseForbidden
from django.conf import settings

def _client_ip(request):
    # Respeta X-Forwarded-For si usas proxy/ingress
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")

class AdminIPAllowlistMiddleware:
    """
    Restringe acceso al prefijo /administracion/ a una allowlist de IPs.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, "ADMIN_IP_ALLOWLIST_ENABLED", False)
        self.paths = getattr(settings, "ADMIN_IP_PROTECTED_PREFIXES", ("/administracion/",))

    def __call__(self, request):
        if self.enabled and any(request.path.startswith(p) for p in self.paths):
            ip = _client_ip(request)
            allow = set(getattr(settings, "ADMIN_IP_ALLOWLIST", []))
            if ip not in allow:
                return HttpResponseForbidden("Acceso restringido por IP")
        return self.get_response(request)
