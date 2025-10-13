# administracion/admin.py
from django.contrib import admin
from .models import AdminAccessLog, AdminUser, Graduate, CertificateType, Template

# --- Helpers para registrar sin duplicar ---
def safe_register(model, admin_class=None):
    """Registra un modelo en el admin solo si no está ya registrado."""
    if model not in admin.site._registry:  # _registry es estable en Django 4.2
        if admin_class:
            admin.site.register(model, admin_class)
        else:
            admin.site.register(model)

# === Admins ===
class AdminAccessLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "username", "event", "ip")
    list_filter = ("event", "created_at")
    search_fields = ("username", "ip", "user_agent")
    readonly_fields = ("created_at",)

# (Opcional) ajusta según necesites
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "is_active", "is_superuser", "created_at")
    search_fields = ("email", "username")
    list_filter = ("is_active", "is_superuser", "created_at")
    readonly_fields = ("created_at", "updated_at")

class GraduateAdmin(admin.ModelAdmin):
    list_display = ("name", "lastname", "email", "completion_date")
    search_fields = ("name", "lastname", "email")

class CertificateTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "abbreviation", "created_at")
    search_fields = ("name", "abbreviation")

class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "file")
    search_fields = ("name",)

# --- Registro seguro (sin decoradores) ---
safe_register(AdminAccessLog, AdminAccessLogAdmin)
safe_register(AdminUser, AdminUserAdmin)
safe_register(Graduate, GraduateAdmin)
safe_register(CertificateType, CertificateTypeAdmin)
safe_register(Template, TemplateAdmin)
