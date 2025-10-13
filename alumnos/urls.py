from django.urls import path
from . import views

app_name = "alumnos"
urlpatterns = [
    path("", views.start, name="start"),
    path("basic/", views.basic, name="basic"),
    path("extras/cproem/", views.extras_cproem, name="extras_cproem"),
    path("extras/dc3/", views.extras_dc3, name="extras_dc3"),
    path("confirm/", views.confirm, name="confirm"),
    path("estatus/", views.status, name="status"),
    path("seguimiento/<int:request_id>/", views.tracking, name="tracking"),

    path("api/tracking/<int:request_id>/", views.tracking_api, name="tracking_api"),
]