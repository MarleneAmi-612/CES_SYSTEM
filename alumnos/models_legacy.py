from django.db import models

class DiplomadoLegacy(models.Model):
    # ajusta los campos a lo que tengas en la tabla de ces_simulacion
    id = models.AutoField(primary_key=True)
    programa = models.CharField(max_length=255, blank=True, null=True)
    programa_full = models.TextField(blank=True, null=True)

    class Meta:
        managed = False  # ¡para que Django no migre esto!
        db_table = "diplomado"
