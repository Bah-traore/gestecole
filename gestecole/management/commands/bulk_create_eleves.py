import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestecole.settings")

import django

django.setup()

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from APP_G2S.models import Eleve, Classe
from gestecole.utils.idgenerateurs import IDGenerator
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = 'Génère 500 élèves de test avec des données réalistes'

    def handle(self, *args, **kwargs):
        fake = Faker('fr_FR')

        try:
            classe = Classe.objects.first()
            if not classe:
                raise Classe.DoesNotExist

            students = []
            with transaction.atomic():
                for i in range(500):
                    tel = f'77{fake.unique.random_number(digits=7)}'

                    student = Eleve(
                        nom=fake.last_name(),
                        prenom=fake.first_name(),
                        telephone=tel,
                        classe=classe,
                        age=fake.random_int(min=12, max=20),
                        residence=fake.city(),
                        prenom_pere=fake.first_name(),
                        nom_pere=fake.last_name(),
                        password=make_password(IDGenerator.generatriceMDP_default()),
                        identifiant=IDGenerator.generate_student_id(classe)
                    )
                    students.append(student)

                    if i % 100 == 0:
                        self.stdout.write(f'Génération {i}/500...')

                Eleve.objects.bulk_create(students, ignore_conflicts=True)

            self.stdout.write(self.style.SUCCESS(f'{len(students)} élèves créés avec succès !'))

        except Classe.DoesNotExist:
            self.stdout.write(self.style.ERROR('Aucune classe trouvée ! Créez-en une d\'abord.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erreur : {str(e)}'))