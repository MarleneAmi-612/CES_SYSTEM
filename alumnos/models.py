# alumnos/models.py
from django.db import models
from django.utils import timezone

# -----------------------------
# Estados admitidos en toda la app
# -----------------------------
STATUS_CHOICES = [
    ("pending", "Pendiente"),
    ("review", "Revisión"),
    ("accepted", "Aprobada"),
    ("rejected", "Rechazada"),
    ("generating", "Generando"),
    ("emailed", "Enviado por correo"),
    ("downloaded", "Descargado por el alumno"),
]


class Program(models.Model):
    """
    Catálogo de programas/diplomados (BD real).
    NOTA: managed=False porque la tabla ya existe y no queremos que Django la migre.
    """
    id = models.BigAutoField(primary_key=True)
    abbreviation = models.CharField(max_length=10)         # siglas (ej. DLIN)
    name = models.CharField(max_length=100)                # nombre completo
    certificate_type = models.ForeignKey(
        "administracion.CertificateType",
        on_delete=models.CASCADE
    )
    status = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "alumnos_program"
        ordering = ["name"]

    def __str__(self):
        # Mostrar siempre el nombre completo en listas/combos
        return self.name or self.abbreviation or f"Programa {self.pk}"


class Request(models.Model):
    """
    Solicitud del alumno para generar su diploma/constancia.
    """
    id = models.BigAutoField(primary_key=True)

    # Datos del alumno
    name = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    email = models.EmailField()

    # Programa cursado
    program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        null=True,
        related_name="requests",
    )

    # Extras opcionales (para constancias)
    curp = models.CharField(max_length=40, null=True, blank=True)
    rfc = models.CharField(max_length=15, null=True, blank=True)
    job_title = models.CharField(max_length=120, null=True, blank=True)
    industry = models.CharField(max_length=200, null=True, blank=True)
    business_name = models.CharField(max_length=200, null=True, blank=True)

    # Estado + motivo
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    status_reason = models.TextField(blank=True, null=True)

    # Tiempos
    sent_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "alumnos_request"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        who = f"{self.name} {self.lastname}".strip() or self.email
        return f"Request #{self.id} · {who}"


class RequestEvent(models.Model):
    """
    Bitácora de cambios de estado.
    Guardamos la primera vez que la solicitud entra a un estado.
    """
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="events",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "alumnos_request_event"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["request", "status"]),
        ]

    def __str__(self):
        return f"#{self.request_id} → {self.status} @ {self.created_at:%Y-%m-%d %H:%M}"
