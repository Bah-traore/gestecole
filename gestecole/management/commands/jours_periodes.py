from django.core.management.base import BaseCommand
from gestecole.utils.academic_manager import gerer_periodes

class Command(BaseCommand):
    help = 'Met à jour les périodes académiques'

    def handle(self, *args, **options):
        gerer_periodes()
        self.stdout.write(self.style.SUCCESS('Périodes académiques mises à jour'))