from django.core.management.base import BaseCommand
from django.utils import timezone
from APP_G2S.models import *


class Command(BaseCommand):
    help = 'Automatise les promotions et clôture la période'

    def handle(self, *args, **options):
        periode = Periode.objects.filter(cloture=False).first()

        if not periode:
            self.stdout.write(self.style.ERROR('Aucune période active trouvée'))
            return

        eleves = Eleve.objects.filter(
            est_expulse=False,
            classe__in=periode.classes.all()
        )

        for eleve in eleves:
            self.traiter_eleve(eleve, periode)

        periode.cloture = True
        periode.save()
        self.stdout.write(self.style.SUCCESS(f'Période {periode} clôturée avec succès'))

    def traiter_eleve(self, eleve, periode):
        try:
            bulletin = BulletinPerformance.objects.get(eleve=eleve, periode=periode)
            paiement_complet = self.verifier_paiements(eleve, periode)

            if bulletin.moyenne_generale >= 30 and paiement_complet:
                self.promouvoir(eleve)
                decision = 'ADMIS'
            else:
                decision = self.gerer_echec(eleve)

            HistoriqueAcademique.objects.create(
                eleve=eleve,
                periode=periode,
                moyenne=bulletin.moyenne_generale,
                decision=decision,
                paiement_complet=paiement_complet
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur élève {eleve}: {str(e)}"))

    def verifier_paiements(self, eleve, periode):
        total_du = Periode.objects.get(periode=periode).montant_total # PeriodePaiement
        total_paye = Paiement.objects.filter(
            eleve=eleve,
            periode__periode=periode,
            statut_paiement='REUSSI'
        ).aggregate(total=Sum('montant_paye'))['total'] or 0

        return total_paye >= total_du
    

    

    def promouvoir(self, eleve):
        nouvelle_classe = getattr(eleve.classe, 'niveau_superieur', None)
        if nouvelle_classe:
            eleve.classe = nouvelle_classe
            eleve.save()
        else:
            self.stdout.write(self.style.WARNING(
                f"Aucune classe supérieure définie pour {eleve.classe} (élève: {eleve})"
            ))

    def gerer_echec(self, eleve):
        eleve.redoublements += 1
        if eleve.redoublements >= 3:
            eleve.est_expulse = True
            decision = 'EXPULSE'
        else:
            decision = 'REDOUBLE'
        eleve.save()
        return decision