from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse

def require_alumnos_session(keys=('alumno_email', 'basic', 'extras')):
    def deco(view):
        @wraps(view)
        def _wrapped(request, *args, **kwargs):
            if not any(k in request.session for k in keys):
                return redirect(reverse('alumnos:start'))
            return view(request, *args, **kwargs)
        return _wrapped
    return deco
