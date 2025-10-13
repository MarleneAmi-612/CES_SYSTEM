from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin,BaseUserManager

class AdminUserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        """
        Crea y guarda un usuario normal de administración
        """
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)  # 🔒 guarda el hash, no la contraseña en claro
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
