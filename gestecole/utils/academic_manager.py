from datetime import date
from django.utils import timezone
from APP_G2S.models import Periode


def gerer_periodes():
    aujourdhui = timezone.now().date()

    periodes = [
        {
            'annee_scolaire': f"{date(2025, 5, 1)} - {date(2026, 5, 30)}",
            'numero': 1,
            'classe': 1,
            'debut': date(2023, 9, 1),
            'fin': date(2023, 12, 15),
            'is_active':True,
            'cloture':True
        },
        {
            'annee_scolaire': f"{date(2025, 5, 1)} - {date(2026, 5, 30)}",
            'numero': 2,
            'classe': 1,
            'debut': date(2024, 1, 8),
            'fin': date(2024, 3, 15),
            'is_active': False,
            'cloture': True
        },
        {
            'annee_scolaire': f"{date(2025, 5, 1)} - {date(2026, 5, 30)}",
            'numero': 3,
            'classe': 1,
            'debut': date(2024, 4, 2),
            'fin': date(2024, 6, 30),
            'is_active': False,
            'cloture': False
        }
    ]

    for p in periodes:
        periode, created = Periode.objects.update_or_create(
            numero=p['numero'],
            annee_scolaire=p['annee_scolaire'],
            defaults={
                'date_debut': p['debut'],
                'date_fin': p['fin'],
                'is_active': aujourdhui > p['fin'],
                'cloture': aujourdhui > p['fin']
            }
        )