from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from administracion import views as admin_views
from django.views.generic import RedirectView

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("administracion:home")
    return redirect("administracion:login")  

urlpatterns = [
    path("administracion/plantillas/import-convert/", admin_views.plantilla_import_convert,name="plantilla_import_convert"),
    path("accounts/profile/",RedirectView.as_view(pattern_name="administracion:home", permanent=False),name="accounts-profile-redirect",),
    path(".well-known/appspecific/com.chrome.devtools.json", admin_views.wellknown_devtools),
    path("accounts/login/",RedirectView.as_view(pattern_name="administracion:login", permanent=False, query_string=True),),
    path("accounts/",RedirectView.as_view(url="/account/", permanent=False, query_string=True),),
    path("", root_redirect, name="root"),
    path('admin/', admin.site.urls),
    path('alumnos/', include(('alumnos.urls', 'alumnos'), namespace='alumnos')),
    path("administracion/", include("administracion.urls", namespace="administracion")),
    path("", include(("ces_system.two_factor_wrapper", "two_factor"), namespace="two_factor")),
    # Aquí después puedes agregar más rutas, por ejemplo:
    # path('', include('alumnos.urls')),
    # path('descarga/', include('descarga.urls')),
    path(
        "favicon.ico",
        RedirectView.as_view(url=settings.STATIC_URL + "favicon/favicon.ico", permanent=True),
    ),
]

# Servir archivos de MEDIA solo en modo DEBUG (desarrollo)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
