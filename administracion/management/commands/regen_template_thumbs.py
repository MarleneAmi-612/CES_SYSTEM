from django.core.management.base import BaseCommand
from administracion.models import DesignTemplate
from administracion.thumbs import save_thumb

class Command(BaseCommand):
    help = "Regenera miniaturas de todas las plantillas (usa --force para sobrescribir)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Sobrescribe miniaturas existentes")

    def handle(self, *args, **opts):
        force = bool(opts.get("force"))
        n = 0
        for tpl in DesignTemplate.objects.all():
            if save_thumb(tpl, force=force):
                tpl.save(update_fields=["thumb"])
                n += 1
        self.stdout.write(self.style.SUCCESS(f"Miniaturas generadas/actualizadas: {n}"))
