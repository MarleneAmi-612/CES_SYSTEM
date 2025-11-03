from django.middleware.csrf import get_token
def csp_nonce(request):
    """
    Expone {{ NONCE }} en templates cuando django-csp
    agrega el nonce a la request (CSP_INCLUDE_NONCE_IN).
    """
    return {"NONCE": getattr(request, "csp_nonce", "")}
def global_vars(request):
    """
    Inyecta variables globales de plantilla:
      - NONCE: para CSP (si django-csp puso nonce en la request)
      - csrf_token: usable en <meta name="csrf-token" ...> etc.
    """
    nonce = getattr(request, "csp_nonce", None)  # lo añade django-csp si CSP_INCLUDE_NONCE_IN contiene 'script-src'/'style-src'
    return {
        "NONCE": nonce,
        "csrf_token": get_token(request),
    }
