from django.core.management.base import BaseCommand
from django.utils import timezone
from alumnos.models import Program
from alumnos.models_ces import Diplomado  # Modelo de la BD externa
from administracion.models import CertificateType

class Command(BaseCommand):
    help = "Sincroniza diplomados desde la base CES a Programs y crea tipos de documento si no existen"

    def handle(self, *args, **kwargs):
        # Crear los 3 tipos de documento si no existen
        diploma, _ = CertificateType.objects.get_or_create(
            name="Diploma",
            defaults={'description': "Documento que acredita la finalización del programa."}
        )
        const0, _ = CertificateType.objects.get_or_create(
            name="Constancia CPROEM",
            defaults={'description': "Constancia según categoría 0 en la BD."}
        )
        const1, _ = CertificateType.objects.get_or_create(
            name="Constancia DC3",
            defaults={'description': "Constancia según categoría 1 en la BD."}
        )

        # Sincronizar programas desde la BD externa
        for d in Diplomado.objects.using('ces').all():
            # Asignar correctamente certificate_type
            if d.constancia == 0:
                cert_type = const0
            elif d.constancia == 1:
                cert_type = const1
            else:
                cert_type = diploma  # Por si hay futuros casos

            #Crear o actualizar registro en Programs
            Program.objects.update_or_create(
                abbreviation=d.programa,
                defaults={
                    'name': d.programa_full,
                    'certificate_type': cert_type,
                    'updated_at': timezone.now()
                }
            )

        self.stdout.write(self.style.SUCCESS("Sincronización de diplomados completada"))
