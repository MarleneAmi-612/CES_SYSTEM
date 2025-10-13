from django.conf import settings
from django.db import models


# Estados admitidos en toda la app (tablero, tracking y eventos)
STATUS_CHOICES = [
    ("pending", "Pendiente"),
    ("review", "Revisión"),
    ("accepted", "Aprobada"),
    ("rejected", "Rechazada"),
    ("generating", "Generando"),
    ("emailed", "Enviado por correo"),
    ("downloaded", "Descargado por el alumno"),
]


class Request(models.Model):
    id = models.BigAutoField(primary_key=True)

    # Datos del alumno
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField()

    # Programa
    program = models.ForeignKey(
        "alumnos.Program",
        on_delete=models.SET_NULL,
        null=True,
        related_name="requests",
    )

    # Extras (opcionales)
    curp = models.CharField(max_length=40, null=True, blank=True)
    rfc = models.CharField(max_length=15, null=True, blank=True)
    job_title = models.CharField(max_length=120, null=True, blank=True)
    industry = models.CharField(max_length=200, null=True, blank=True)
    business_name = models.CharField(max_length=200, null=True, blank=True)

    # Estado actual + motivo opcional (se usa cuando es rechazado, etc.)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    status_reason = models.TextField(blank=True, null=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alumnos_request"  # usa el que tengas realmente; si ya existe, respétalo
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Request #{self.id} - {self.email}"


class Program(models.Model):
    id = models.BigAutoField(primary_key=True)
    abbreviation = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    certificate_type = models.ForeignKey("administracion.CertificateType", on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "alumnos_program"

    def __str__(self):
        return self.abbreviation or self.name


class RequestEvent(models.Model):
    """
    Bitácora de cambios de estado para mostrar en el tracking.
    Guardamos solo el PRIMER instante en el que se entra a cada estado.
    """
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="events",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alumnos_request_event"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["request", "status"]),
        ]

    def __str__(self):
        return f"#{self.request_id} → {self.status} @ {self.created_at:%Y-%m-%d %H:%M}"
