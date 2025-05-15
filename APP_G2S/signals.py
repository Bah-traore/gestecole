from django.db.models.signals import pre_save
from django.dispatch import receiver
from APP_G2S.models import *

@receiver(pre_save, sender=Note)
@receiver(pre_save, sender=Paiement)
def verifier_periode_fermee(sender, instance, **kwargs):
    if instance.periode.cloture:
        raise ValidationError("Modification impossible : période clôturée")