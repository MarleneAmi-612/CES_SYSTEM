from django.urls import path, reverse_lazy
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.http import JsonResponse, HttpResponse
from .forms import AdminAuthForm
from .views import (
    AdminHomeView,
    password_change_inline,
    create_admin_inline,
    RequestsBoardView,
    request_update_status,
    plantillas,
    egresados,
    doc_preview,
    doc_download,
    doc_send,
    doc_confirm,
    egresados_preview_pdf,
    verificar_token,
    egresado_update,
)
from . import views

app_name = "administracion"

urlpatterns = [
    # Auth
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

    # Password reset
    path(
        "password/reset/",
        PasswordResetView.as_view(
            template_name="administracion/password_reset_form.html",
            email_template_name="administracion/password_reset_email.txt",
            subject_template_name="administracion/password_reset_subject.txt",
            success_url=reverse_lazy("administracion:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password/reset/hecho/",
        PasswordResetDoneView.as_view(
            template_name="administracion/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="administracion/password_reset_confirm.html",
            success_url=reverse_lazy("administracion:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/completo/",
        PasswordResetCompleteView.as_view(
            template_name="administracion/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path(".well-known/appspecific/com.chrome.devtools.json",
         lambda r: HttpResponse(status=204)),
    
    # Endpoints inline (AJAX)
    path("password/change-inline/", password_change_inline, name="password_change_inline"),
    path("users/create-admin-inline/", create_admin_inline, name="create_admin_inline"),

    # Tablero solicitudes
    path("solicitudes/", RequestsBoardView.as_view(), name="requests_board"),
    path("solicitudes/estado/", request_update_status, name="request_update_status"),
    path(
        "solicitudes/<int:pk>/eliminar-rechazada/",
        views.request_delete_rejected,
        name="request_delete_rejected",
    ),
    # Plantillas (portada + variante con req_id) — nombres distintos
    path("plantillas/", plantillas, name="plantillas"),
    path("plantillas/<int:req_id>/", plantillas, name="plantillas_req"),
    path("plantillas/admin/<int:tpl_id>/thumb/upload/", views.plantilla_upload_thumb, name="plantilla_upload_thumb"),
    path("plantillas/admin/<int:tpl_id>/thumb/regen/", views.plantilla_regen_thumb, name="plantilla_regen_thumb"),
    path("plantillas/import/convert/", views.import_office_to_image, name="plantilla_import_convert"),

   # Egresados
    path("egresados/", egresados, name="egresados"),
    path("egresados/<int:req_id>/", egresados, name="egresados_req"),
    path("egresados/<int:req_id>/guardar/", egresado_update, name="egresado_update"),
    path("egresados/<int:req_id>/guardar-inline/", egresado_update, name="egresado_update_inline"),
    path("egresados/<int:req_id>/update/", views.egresado_update, name="egresado_update"),
    path("egresados/inline/update/", views.egresado_update_inline, name="egresado_update_inline"),
    path("egresados/email-preview/<int:req_id>/", views.doc_email_preview, name="doc_email_preview"),

    # Acciones documento
    path("egresados/<int:req_id>/preview/", doc_preview, name="doc_preview"),
    path("egresados/<int:req_id>/download/", doc_download, name="doc_download"),
    path("egresados/<int:req_id>/send/", doc_send, name="doc_send"),
    path("egresados/<int:req_id>/confirm/", doc_confirm, name="doc_confirm"),
    path("egresados/<int:req_id>/preview.pdf", egresados_preview_pdf, name="egresados_preview_pdf"),

    # Verificación pública por token (QR)
    path("verificar/<str:token>/", verificar_token, name="verificar_token"),

    # Catálogo y admin de plantillas / assets
    path("plantillas/catalogo/", views.plantillas_catalogo, name="plantillas_catalogo"),
    path("plantillas/importar/", views.plantilla_import, name="plantilla_import"),
    path("plantillas/admin/", views.plantillas_admin, name="plantillas_admin"),
    path("plantillas/admin/nueva/", views.plantilla_create, name="plantilla_create"),
    path("plantillas/admin/<int:tpl_id>/", views.plantilla_edit, name="plantilla_edit"),
    path("plantillas/admin/<int:tpl_id>/duplicar/", views.plantilla_duplicate, name="plantilla_duplicate"),
    path("plantillas/admin/<int:tpl_id>/version/", views.plantilla_new_version, name="plantilla_new_version"),
    path("plantillas/admin/<int:tpl_id>/eliminar/", views.plantilla_delete, name="plantilla_delete"),
    path("plantillas/admin/importar/", views.plantilla_import, name="plantilla_import"),
    path("plantillas/assets/", views.assets_library, name="assets_library"),
    path("plantillas/assets/upload/", views.asset_upload, name="asset_upload"),
    path("plantillas/assets/delete/<int:pk>/", views.asset_delete, name="asset_delete"),  # <-- NUEVO
    path("assets/<int:asset_id>/convert-image/", views.asset_convert_to_image, name="asset_convert_to_image"),
    path("plantillas/import/convert/", views.plantilla_import_convert, name="plantilla_import_convert"),


    # Programas
    path("programas/", views.program_list, name="program_list"),
    path("programas/nuevo/", views.program_create, name="program_create"),
    path("programas/<int:pk>/editar/", views.program_edit, name="program_edit"),
    path("programas/<int:pk>/eliminar/", views.program_delete, name="program_delete"),
    path("programas/bulk-delete/", views.program_bulk_delete, name="program_bulk_delete"),
    path("programas/<str:source>/<int:pk>/eliminar/", views.program_delete, name="program_delete"),
    #path("programas/<int:pk>/edit-api/",views.program_edit_api,name="program_edit_api",),
    path("programas/bulk-delete/", views.program_bulk_delete, name="program_bulk_delete"),
     path(
        "cproem/digital/<int:graduate_id>/",
        views.pdf_cproem_digital,
        name="pdf_cproem_digital",
    ),
    path(
        "cproem/impreso/<int:graduate_id>/",
        views.pdf_cproem_impreso,
        name="pdf_cproem_impreso",
    ),
]

