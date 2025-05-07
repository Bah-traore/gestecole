import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestecole.settings')

app = Celery('gestecole')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.beat_schedule = {
    'generer-absences': {
        'task': 'APP_G2S.tasks.generer_absences_auto',
        'schedule': crontab(hour=2, minute=30),
    },
}
app.autodiscover_tasks()

#
# @shared_task
# def generer_bulletins_async(eleve_ids, classe_id, utilisateur_id):
#     # Même logique que votre vue mais en tâche de fond
#     return result