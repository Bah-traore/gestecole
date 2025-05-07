from datetime import date, timedelta
from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string

from APP_G2S.models import EmploiDuTemps, Note, Absence, PeriodePaiement, ApprovalRequest
from gestecole.utils.idgenerateurs import SMSService
from gestecole.utils.paiements import SuspensionService
from django.utils import timezone
from APP_G2S.models import Examen, Periode






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
    # Envoyer des rappels
        if periode.date_fin - aujourdhui <= timedelta(days=3):
            for eleve in periode.classe.eleves.all():
                if not eleve.paiements.filter(periode=periode, statut=True).exists():

                    SMSService.send_sms(
                        eleve.telephone_parent,
                        f"Rappel paiement {periode.nom}: {periode.montant}FCFA - Échéance {periode.date_fin}"
                    )

    # Après échéance
    if periode.date_fin < aujourdhui:
        for eleve in periode.classe.eleves.all():
            if not eleve.paiements.filter(periode=periode, statut=True).exists():
                eleve.suspendu = True
            eleve.save()
            SuspensionService.verifier_suspension(eleve)
            SMSService.send_sms(
                eleve.telephone_parent,
                f"URGENT: Paiement {periode.nom} en retard! Suspension imminente"
            )