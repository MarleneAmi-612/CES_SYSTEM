from django.urls import path, reverse_lazy
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from .forms import AdminAuthForm
from .views import (
    AdminHomeView,
    password_change_inline,
    create_admin_inline,
    RequestsBoardView,
    request_update_status,   # <-- ya importado; no uses "views."
)

app_name = "administracion"

urlpatterns = [
    # Acceso
    path(
        "acceso/",
        LoginView.as_view(
            template_name="administracion/login.html",
            authentication_form=AdminAuthForm,
            redirect_authenticated_user=True,
            extra_context={"page_title": "Acceso | Administración CES"},
        ),
        name="login",
    ),
    path("salir/", LogoutView.as_view(), name="logout"),

    # Home
    path("", AdminHomeView.as_view(), name="home"),

    # Password reset clásico (por correo)
    path("password/reset/", PasswordResetView.as_view(
        template_name="administracion/password_reset_form.html",
        email_template_name="administracion/password_reset_email.txt",
        subject_template_name="administracion/password_reset_subject.txt",
        success_url=reverse_lazy("administracion:password_reset_done"),
    ), name="password_reset"),
    path("password/reset/hecho/", PasswordResetDoneView.as_view(
        template_name="administracion/password_reset_done.html"
    ), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name="administracion/password_reset_confirm.html",
        success_url=reverse_lazy("administracion:password_reset_complete"),
    ), name="password_reset_confirm"),
    path("password/reset/completo/", PasswordResetCompleteView.as_view(
        template_name="administracion/password_reset_complete.html"
    ), name="password_reset_complete"),

    # Endpoints inline (AJAX desde los modales)
    path("password/change-inline/", password_change_inline, name="password_change_inline"),
    path("users/create-admin-inline/", create_admin_inline, name="create_admin_inline"),

    # Tablero de solicitudes + cambio de estado
    path("solicitudes/", RequestsBoardView.as_view(), name="requests_board"),
    path("solicitudes/estado/", request_update_status, name="request_update_status"),
]
