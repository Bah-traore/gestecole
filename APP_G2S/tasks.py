from datetime import date, timedelta
from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string

from APP_G2S import models
from APP_G2S.models import EmploiDuTemps, Note, Absence, PeriodePaiement, ApprovalRequest, Paiement
from gestecole.utils.messageries import SmsOrangeService
from gestecole.utils.paiements import SuspensionService
from django.utils import timezone
from APP_G2S.models import Examen, Periode


@shared_task
def envoyer_notifications_initiales(periode_id):
    periode = PeriodePaiement.objects.get(id=periode_id)
    for classe in periode.classe.all():
        for eleve in classe.eleves.all():
            message = (
                f"Nouvelle obligation de paiement :\n"
                f"Période : {periode.nom}\n"
                f"Montant total : {periode.montant} FCFA\n"
                f"Échéance : {periode.date_fin.strftime('%d/%m/%Y')}\n"
                f"Paiement échelonné : {'Oui' if periode.allow_installments else 'Non'}"
            )
            sms_service = SmsOrangeService()
            sms_service.envoyer_sms_orange(eleve.telephone, message)



@shared_task
def verifier_paiements_echelonnes(periode_id=None):
    today = timezone.now().date()

    if periode_id:
        # Si un ID de période est fourni, vérifier uniquement cette période
        periodes = PeriodePaiement.objects.filter(id=periode_id)
    else:
        # Sinon, vérifier toutes les périodes actives avec paiements échelonnés
        periodes = PeriodePaiement.objects.filter(
            allow_installments=True,
            date_fin__gte=today
        )

    for periode in periodes:
        for classe in periode.classe.all():
            for eleve in classe.eleves.all():
                total_paye = eleve.paiements.filter(
                    periode=periode,
                    statut_paiement='REUSSI'
                ).aggregate(total=models.Sum('montant_paye'))['total'] or 0

                reste = periode.montant_total - total_paye

                if reste > 0:
                    message = (
                        f"Rappel paiement échelonné :\n"
                        f" {periode.nom}\n"
                        f" Reste à payer : {reste} FCFA\n"
                        f" Total initial : {periode.montant} FCFA\n"
                        f" Avant le : {periode.date_fin.strftime('%d/%m/%Y')}"
                    )
                    sms_service = SmsOrangeService()
                    sms_service.envoyer_sms_orange(eleve.telephone, message)

def planifier_rappels(periode_id):
    periode = PeriodePaiement.objects.get(id=periode_id)
    date_rappel = periode.date_fin - timezone.timedelta(days=3)
    verifier_paiements_echelonnes.apply_async(
        (periode_id,),
        eta=date_rappel
    )


@shared_task
def verifier_paiements_incomplets():
    # Vérifier les paiements partiels non complétés avant échéance
    periodes = PeriodePaiement.objects.filter(
        date_fin__gte=timezone.now() - timedelta(days=1)
    )

    for periode in periodes:
        paiements = Paiement.objects.filter(
            periode=periode,
            statut_paiement='PARTIEL',
            created_at__lte=timezone.now() - timedelta(hours=24)
        )

        for paiement in paiements:
            if paiement.solde_restant > 0:
                message = (
                    f"Rappel paiement échelonné :\n"
                    f"{periode.nom}\n"
                    f"Reste à payer : {paiement.solde_restant} FCFA\n"
                    f"Avant le : {periode.date_fin.strftime('%d/%m/%Y')}"
                )
                paiement.eleve.envoyer_sms_parent(message)
                paiement.date_rappel = timezone.now()
                paiement.save()



@shared_task
def generer_absences_auto():
    # Récupérer les emplois non traités et passés
    emplois = EmploiDuTemps.objects.filter(
        date__lt=date.today(),
        processed=False
    )

    for emploi in emplois:
        # Pour chaque élève de la classe
        for eleve in emploi.classe.eleves.all():
            # Vérifier si une note existe pour ce cours
            if not Note.objects.filter(emploi_du_temps=emploi, eleve=eleve).exists():
                # Créer l'absence automatique
                Absence.objects.get_or_create(
                    eleve=eleve,
                    emploi_du_temps=emploi,
                    defaults={'motif': 'Absence non justifiée (automatique)'}
                )
        emploi.processed = True
        emploi.save()


@shared_task
def verifier_impayes():
    periodes_expirees = PeriodePaiement.objects.filter(
        date_fin__lt=timezone.now()
    )

    for periode in periodes_expirees:
        for eleve in periode.classe.eleves.all():
            if not eleve.paiements.filter(periode=periode, statut=True).exists():
                eleve.envoyer_sms_parent(
                    f"URGENT: Impayé pour {periode.nom} - {periode.montant} FCFA"
                )
                eleve.suspendu = True
                eleve.save()

@shared_task
def notify_approvers(approval_id):
    approval = ApprovalRequest.objects.get(pk=approval_id)

    # Trouver les approbateurs selon le type d'action
    approvers = User.objects.filter(
        groups__name__in=approval.get_approvers()
    )

    for user in approvers:
        send_mail(
            f"Demande d'approbation pour {approval.action_type}",
            render_to_string('emails/approval_request.txt', {'approval': approval}),
            'noreply@ecole.ml',
            [user.email]
        )



@shared_task
def update_exam_status():
    exams_to_close = Examen.objects.filter(
        date_fin__lt=timezone.now().date(),
        validite='EN_COURS'
    )
    exams_to_close.update(validite='FIN')

    # Mettre à jour les périodes clôturées
    periods_to_close = Periode.objects.filter(
        date_fin__lt=timezone.now().date(),
        cloture=False
    )
    periods_to_close.update(cloture=True)


@shared_task
def verifier_impayes():
    aujourdhui = timezone.now().date()
    periodes = PeriodePaiement.objects.filter(
        date_debut__lte=aujourdhui,
        date_fin__gte=aujourdhui - timedelta(days=3)
    ) # Rappel 3 jours avant la fin

    for periode in periodes:
        if periode.date_fin - aujourdhui <= timedelta(days=3):
            for eleve in periode.classe.eleves.all():
                if not eleve.paiements.filter(periode=periode, statut=True).exists():

                    sms_service = SmsOrangeService()
                    sms_service.envoyer_sms_orange(
                        eleve.telephone,
                        f"Rappel paiement {periode.nom}: {periode.montant}FCFA - Échéance {periode.date_fin}"
                    )

    # Après échéance
    if periode.date_fin < aujourdhui:
        for eleve in periode.classe.eleves.all():
            if not eleve.paiements.filter(periode=periode, statut=True).exists():
                eleve.suspendu = True
            eleve.save()
            SuspensionService.verifier_suspension(eleve)
            sms_service = SmsOrangeService()
            sms_service.envoyer_sms_orange(
                eleve.telephone,
                f"URGENT: Paiement {periode.nom} en retard! Suspension imminente"
            )
