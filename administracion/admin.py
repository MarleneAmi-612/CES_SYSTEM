from django.contrib import admin
from .models import DiplomaBackground,DesignTemplate,TemplateAsset,AdminAccessLog, AdminUser, Graduate, CertificateType, Template, Program,DesignTemplateVersion,Organization
from .models import DocxTemplate

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

#Plantillas

@admin.register(TemplateAsset)
class TemplateAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "mime", "org", "created_at")
    search_fields = ("name",)

class DesignTemplateVersionInline(admin.TabularInline):
    model = DesignTemplateVersion
    extra = 0
    fields = ("version", "note", "created_by", "created_at")
    readonly_fields = ("created_at",)

@admin.register(DesignTemplate)
class DesignTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "updated_at")
    list_filter = ("kind", "is_system")
    search_fields = ("title",)

    fieldsets = (
        (None, {
            "fields": ("title", "kind", "thumb", "json_active", "is_system")
        }),
        ("Fondos (CPROEM)", {
            "fields": ("background_web", "background_print"),
            "description": "Opcional: fondos usados para CPROEM WEB/IMPRESA"
        }),
    )


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code","name","constancia_type","is_active","updated_at")
    search_fields = ("code","name")
    list_filter = ("constancia_type","is_active")

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
    
@admin.register(DiplomaBackground)
class DiplomaBackgroundAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)
    
@admin.register(DocxTemplate)
class DocxTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "tipo", "is_active", "created_at")
    list_filter  = ("tipo", "is_active")
    search_fields = ("name",)