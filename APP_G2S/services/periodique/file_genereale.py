from APP_G2S.models import *

def get_active_period():
    try:
        activad_periode=Periode.objects.get(is_active=True)
    except Exception as e:
        return None
    return activad_periode


# creer une gestion de verification des periodes toute confondus

class FiltreService:
    @staticmethod
    def get_academie_years():
        """Retourne la liste des années scolaires distinctes au format 'AAAA-AAAA'"""
        periodes = Periode.objects.all()
        annees = set()
        for p in periodes:
            start_year = p.date_debut.year
            end_year = p.date_fin.year
            annees.add(f"{start_year} - {end_year}")
        return sorted(annees, reverse=True)

    @staticmethod
    def get_classes(academic_year=None):
        """Filtre les classes selon l'année scolaire ou la période active"""
        if academic_year:
            start, end = academic_year.split('-')
            periodes = Periode.objects.filter(
                date_debut__year=start,
                date_fin__year=end
            )
            return Classe.objects.filter(periode__in=periodes).distinct()
        else:
            periode_active = Periode.objects.filter(is_active=True).first()
            return periode_active.classe.all() if periode_active else Classe.objects.none()

    @staticmethod
    def get_archived_data():
        """Récupère les données des périodes clôturées"""
        periodes_cloturees = Periode.objects.filter(cloture=True)
        return {
            'notes': Note.objects.filter(periode__in=periodes_cloturees),
            'bulletins': BulletinPerformance.objects.filter(periode__in=periodes_cloturees),
            'paiements': Paiement.objects.filter(periode__in=periodes_cloturees)
        }