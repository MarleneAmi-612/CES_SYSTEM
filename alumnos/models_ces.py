from django.db import models

class Alumnos(models.Model):
    id = models.IntegerField(primary_key=True)
    correo = models.CharField(max_length=255, unique=True)
    # Campos opcionales para validar identidad contra la BD de CES
    nombre = models.CharField(max_length=255, null=True, blank=True)
    apellido = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'alumnos'


class Diplomado(models.Model):
    id = models.IntegerField(primary_key=True)
    programa = models.CharField(max_length=50)          # abreviación
    programa_full = models.CharField(max_length=200)    # nombre completo
    constancia = models.IntegerField()                  # 0 o 1

    class Meta:
        managed = False
        db_table = 'diplomado'
