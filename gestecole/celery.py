import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestecole.settings')


app = Celery('gestecole')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Planification automatique des tâches récurrentes
app.conf.beat_schedule = {
    'verifier-paiements-incomplets': {
        'task': 'APP_G2S.tasks.verifier_paiements_incomplets',
        'schedule': 3600,  # Toutes les heures
    },
    'mise-a-jour-statut-examens': {
        'task': 'APP_G2S.tasks.update_exam_status',
        'schedule': 86400,  # Quotidien
    },
}

