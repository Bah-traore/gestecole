from datetime import datetime


class OrangeMoneyAPI:
    def initier_paiement(montant, telephone):
        # Implémentation API Orange Money
        pass

class MalitelMoneyAPI:
    def initier_paiement(montant, telephone):
        # Implémentation API Malitel M-Money
        pass

class SuspensionService:
    @staticmethod
    def verifier_suspension(eleve):
        paiements_en_retard = eleve.paiements.filter(
            periode__date_fin__lt=datetime.today(),
            statut=False
        )
        eleve.suspendu = paiements_en_retard.exists()
        eleve.save()
        return eleve.suspendu