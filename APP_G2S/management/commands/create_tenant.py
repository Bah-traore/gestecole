import random
import string
from django.core.management.base import BaseCommand
from APP_G2S.models import Tenant

class Command(BaseCommand):
    help = 'Crée un nouveau tenant (école) pour le système multi-tenant'

    def add_arguments(self, parser):
        parser.add_argument('nom', type=str, help='Nom de l\'école')
        parser.add_argument('--subdomain', type=str, help='Sous-domaine pour l\'école (généré automatiquement si non fourni)')
        parser.add_argument('--adresse', type=str, help='Adresse de l\'école')
        parser.add_argument('--email', type=str, help='Email de contact de l\'école')
        parser.add_argument('--telephone', type=str, help='Téléphone de l\'école')
        parser.add_argument('--site-web', type=str, help='Site web de l\'école')
        parser.add_argument('--description', type=str, help='Description de l\'école')

    def handle(self, *args, **options):
        nom = options['nom']

        # Générer un sous-domaine si non fourni
        subdomain = options.get('subdomain')
        if not subdomain:
            # Convertir le nom en sous-domaine (enlever les espaces, caractères spéciaux, etc.)
            subdomain = ''.join(c.lower() for c in nom if c.isalnum())

            # Vérifier si le sous-domaine existe déjà, ajouter un suffixe aléatoire si nécessaire
            if Tenant.objects.filter(subdomain=subdomain).exists():
                random_suffix = ''.join(random.choices(string.digits, k=4))
                subdomain = f"{subdomain}{random_suffix}"

        # Créer le tenant
        tenant = Tenant.objects.create(
            nom=nom,
            subdomain=subdomain,
            adresse=options.get('adresse', ''),
            email=options.get('email', ''),
            telephone=options.get('telephone', ''),
            site_web=options.get('site_web', 'http://example.com'),  # Valeur par défaut pour éviter les erreurs NULL
            description=options.get('description', ''),
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f'Tenant "{nom}" créé avec succès!'))
        self.stdout.write(f'Sous-domaine: {subdomain}')
        self.stdout.write(f'ID: {tenant.id}')
        self.stdout.write(f'Pour accéder à ce tenant en développement, utilisez: http://localhost:8000/?tenant_id={tenant.id}')
