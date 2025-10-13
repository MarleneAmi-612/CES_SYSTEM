from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("administracion:home")
    return redirect("administracion:login")  

urlpatterns = [
    path("", root_redirect, name="root"),
    path('admin/', admin.site.urls),
    path('alumnos/', include(('alumnos.urls', 'alumnos'), namespace='alumnos')),
    path("administracion/", include("administracion.urls", namespace="administracion")),
    path("", include(("ces_system.two_factor_wrapper", "two_factor"), namespace="two_factor")),
    # Aquí después puedes agregar más rutas, por ejemplo:
    # path('', include('alumnos.urls')),
    # path('descarga/', include('descarga.urls')),
]

# Servir archivos de MEDIA solo en modo DEBUG (desarrollo)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
