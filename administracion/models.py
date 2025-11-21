import os
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin,BaseUserManager
from alumnos.models import Request
from django.urls import reverse
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
class AdminUserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        """
        Crea y guarda un usuario normal de administración
        """
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")

        email = self.normalize_email(email)
        # por si acaso
        extra_fields.setdefault("is_active", True)

        user = self.model(
            email=email,
            username=username,
            **extra_fields,
        )
        if password:
            user.set_password(password)  # 🔒 guarda el hash
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        """
        Crea y guarda un superusuario de administración
        """
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True")

        return self.create_user(email, username, password, **extra_fields)


class AdminUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=254)
    username = models.CharField(max_length=100, unique=True, null=True, blank=True)

    # 🔹 NUEVOS CAMPOS PARA EL PERFIL
    first_name = models.CharField("nombre", max_length=150, blank=True)
    last_name  = models.CharField("apellidos", max_length=150, blank=True)

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = AdminUserManager()

    def __str__(self):
        return self.email
# === Modelo Graduate ===
class Graduate(models.Model):
    id = models.BigAutoField(primary_key=True)

    # 🔹 NUEVO: vínculo con la solicitud
    request = models.OneToOneField(
        'alumnos.Request',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graduate'
    )

    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, unique=True)
    curp = models.CharField(max_length=40, unique=True)
    job_title = models.CharField(max_length=120, blank=True, null=True)
    industry = models.CharField(max_length=200, blank=True, null=True)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)

    validity_start = models.DateField(blank=True, null=True)
    validity_end = models.DateField(blank=True, null=True)
    download_date = models.DateField(blank=True, null=True)
    diploma_file = models.CharField(max_length=100, blank=True, null=True)
    qr_image = models.CharField(max_length=100, blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    completion_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} {self.lastname}"


# === Modelo CertificateType ===
class CertificateType(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    abbreviation = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# === Modelo Template (plantillas de diplomas) ===
class Template(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to="templates/")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# === Modelo AdminAccessLog (seguridad) ===
class AdminAccessLog(models.Model):
    EVENT_LOGIN_SUCCESS = "login_success"
    EVENT_LOGIN_FAILURE = "login_failure"
    EVENT_LOGOUT = "logout"

    EVENT_CHOICES = [
        (EVENT_LOGIN_SUCCESS, "Login OK"),
        (EVENT_LOGIN_FAILURE, "Login fallo"),
        (EVENT_LOGOUT, "Logout"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_access_logs",
    )
    username = models.CharField(max_length=254)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    event = models.CharField(max_length=32, choices=EVENT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    session_key = models.CharField(max_length=40, blank=True, null=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["username", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at} {self.username} {self.event}"

class DocToken(models.Model):
    TIPO_CHOICES = (
        ("diploma", "Diploma"),
        ("dc3", "DC3"),
        ("cproem", "CPROEM"),
    )

    request = models.ForeignKey(
        "alumnos.Request",
        related_name="doc_tokens",
        on_delete=models.CASCADE,
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Solo un token activo por (request, tipo)
        constraints = [
            models.UniqueConstraint(
                fields=["request", "tipo"],
                condition=models.Q(is_active=True),
                name="uniq_request_tipo_active"
            )
        ]

    def __str__(self):
        return f"{self.request_id} - {self.tipo} - {self.token}"

    def get_absolute_url(self):
        return reverse("administracion:verificar", args=[self.token])
    
# Plantillas 
# === NUEVO: Tipos de constancia compatibles con tus PDFs
class ConstanciaType(models.TextChoices):
    CEPROEM = "CEPROEM", "CEPROEM"
    DC3     = "DC3", "DC3"

# === NUEVO: Activos gráficos (logos/fondos) para plantillas
class TemplateAsset(models.Model):
    name = models.CharField(max_length=120)
    file = models.FileField(upload_to="assets/plantillas/")
    mime = models.CharField(max_length=80, blank=True, null=True)
    # Alcance: global o por organización (si usas orgs)
    org = models.ForeignKey("administracion.Organization", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.name

# === NUEVO: Plantilla de diseño (metadatos)
class DesignTemplate(models.Model):
    DOC = "doc"; SLIDE = "slide"; DESIGN = "design"
    KIND_CHOICES = [(DOC,"Doc"), (SLIDE,"Slide"), (DESIGN,"Design")]

    title = models.CharField(max_length=200)
    kind  = models.CharField(max_length=10, choices=KIND_CHOICES, default=DESIGN)
    json_active = models.JSONField(default=dict, blank=True)
    thumb = models.ImageField(upload_to="plantillas/thumbs/", null=True, blank=True)
    is_system = models.BooleanField(default=False)
    org = models.ForeignKey("administracion.Organization", null=True, blank=True, on_delete=models.SET_NULL)

    # 🔥 NUEVO — Fondos dinámicos CPROEM
    background_web = models.FileField(
        upload_to="plantillas/backgrounds/",
        null=True, blank=True,
        help_text="Fondo WEB (vista previa y tracking)"
    )

    background_print = models.FileField(
        upload_to="plantillas/backgrounds/",
        null=True, blank=True,
        help_text="Fondo IMPRESO (descarga final)"
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): 
        return f"{self.title} ({self.kind})"

    # === NUEVO: métodos seguros para obtener URLs ===
    def get_background_web_url(self):
        from django.templatetags.static import static
        if self.background_web:
            return self.background_web.url
        return static("img/diplomas/Diploma_CPROEM_WEB.png")

    def get_background_print_url(self):
        from django.templatetags.static import static
        if self.background_print:
            return self.background_print.url
        return static("img/diplomas/Constancia_CPROEM_impresa.png")


# === NUEVO: Versionado de plantillas (para "actualizar archivo")
class DesignTemplateVersion(models.Model):
    template = models.ForeignKey(DesignTemplate, on_delete=models.CASCADE, related_name="versions")
    version  = models.PositiveIntegerField()
    # contenido serializado (ProseMirror o capas tipo Konva)
    json_payload = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=200, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("template","version")]
        ordering = ["-version"]

# === NUEVO: Diplomados/Programas (ya NO dependen de ces_simulacion)
class Program(models.Model):
    name = models.CharField(max_length=240, unique=True)
    code = models.CharField(max_length=60, unique=True)  # para URLs/QR/folio
    constancia_type = models.CharField(max_length=10, choices=ConstanciaType.choices, default=ConstanciaType.CEPROEM)

    # (Opcional) Plantillas por tipo de documento
    plantilla_diploma   = models.ForeignKey(DesignTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="program_diploma")
    plantilla_constancia = models.ForeignKey(DesignTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="program_constancia")

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.code} — {self.name}"
class Organization(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"

    def __str__(self):
        return self.name

# === Mapeo a la tabla legacy ces_simulacion.diplomado ===
class ProgramSim(models.Model):
    """
    Mapea la tabla REAL 'diplomado' de ces_simulacion.
    """
    id = models.AutoField(primary_key=True, db_column="id")

    # código corto
    abbreviation = models.CharField(
        "Código",
        max_length=50,
        db_column="programa"
    )

    # nombre completo
    name = models.CharField(
        "Nombre completo",
        max_length=255,
        db_column="programa_full"
    )

    # tipo de constancia (0 = CPROEM, 1 = DC3)
    certificate_type = models.IntegerField(
        "Tipo de constancia",
        db_column="constancia"
    )

    # ESTA ES LA ÚNICA FECHA QUE EXISTE EN LA TABLA REAL
    updated_at = models.DateTimeField(db_column="update_at", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "diplomado"

    def __str__(self):
        return f"{self.abbreviation} — {self.name}"

class DiplomaBackground(models.Model):
    # código del diplomado: DAIE, DAP, DTC, etc.
    code = models.CharField("Código", max_length=20, unique=True)

    # nombre completo del diplomado (opcional, solo para que se vea bonito en admin)
    name = models.CharField("Nombre programa", max_length=255, blank=True)

    # archivo de imagen que antes ponías en static/img/diplomas
    image = models.ImageField(
        "Imagen de fondo",
        upload_to="diplomas/",   # se guardará en MEDIA_ROOT/diplomas/
    )

    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        verbose_name = "Fondo de diploma"
        verbose_name_plural = "Fondos de diploma"

    def __str__(self):
        return f"{self.code} - {self.name or self.image.name}"
    
@receiver(post_delete, sender=DiplomaBackground)
def delete_bg_file_on_delete(sender, instance, **kwargs):
    """
    Cuando borras la plantilla en admin, se borra también el archivo físico.
    """
    if instance.image:
        instance.image.delete(save=False)


@receiver(pre_save, sender=DiplomaBackground)
def delete_old_file_on_change(sender, instance, **kwargs):
    """
    Si cambias la imagen en una plantilla existente, borra el archivo anterior.
    """
    if not instance.pk:
        return  # es nueva, no hay archivo viejo

    try:
        old = DiplomaBackground.objects.get(pk=instance.pk)
    except DiplomaBackground.DoesNotExist:
        return

    old_file = old.image
    new_file = instance.image

    if old_file and old_file != new_file:
        old_file.delete(save=False)    

class RejectedArchive(models.Model):
    email = models.EmailField(db_index=True)
    full_name = models.CharField(max_length=255)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} <{self.email}>"
