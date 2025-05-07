import logging
import random
import string
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)

# Ajouter cette fonction dans services.py
class IDGenerator:
    @staticmethod
    def generate_teacher_id():
        from APP_G2S.models import Enseignant
        """Génère un identifiant unique pour un enseignant (format: ENSXXXXXX)"""
        last_id = Enseignant.objects.order_by('-id').first()
        if last_id:
            new_num = int(last_id.id) + 1
        else:
            new_num = 1
        return f"ENS{str(new_num).zfill(6)}"

    @staticmethod
    def generatriceMDP_default(longueur=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(characters) for _ in range(longueur))

    @staticmethod
    def generate_student_id(classe):
        from APP_G2S.models import Eleve
        """Génère un identifiant unique pour un élève (format: CLASSE-ANNEE-XXXX)"""
        year = timezone.now().year % 100  # Deux derniers chiffres de l'année
        last_student = Eleve.objects.filter(classe=classe).order_by('-id').first()
        if last_student:
            last_num = int(last_student.id) + 1
        else:
            last_num = 1
        return f"{classe.niveau}{classe.section}-{year}-{str(last_num).zfill(4)}"

class SMSService:
    @staticmethod
    def send_creation_sms(enseignant, password): # password
        if not enseignant.telephone:
            return False

        message = (
            f"Bienvenue {enseignant.nom_complet}!\n"
            f"Identifiant: {enseignant.identifiant}\n"
            f"Mot de passe temporaire: {password}\n"
            f"Valide 15 minutes. A changer après connexion."
        )


        # Simulation d'envoi SMS
        print(f"SMS envoyé à {enseignant.telephone}: {message}")
        return True

    @staticmethod
    def send_creation_sms_eleve(eleve, password): # password
        if not eleve.telephone:
            return False
        message = ''
        try:
            message = (
                f"Bienvenue {eleve.prenom} {eleve.nom}!\n"
                f"Identifiant: {eleve.identifiant}\n"
                f"Mot de passe temporaire: {password}\n"
                f"Valide 15 minutes. A changer après connexion."
            )
        except Exception as e:
            print("[ERREUR]: messagerie", str(e))

        print(f"SMS envoyé à {eleve.telephone}: {message}")
        return True

    @staticmethod
    def send_sms(numero, message, sender_id=None):
        """
        Envoi de SMS via API Orange/Malitel
        Args:
            numero (str): Numéro destinataire (format international +223...)
            message (str): Contenu du message
            sender_id (str): ID de l'expéditeur approuvé
        Returns:
            bool: True si succès
        """
        # Configuration
        provider = getattr(settings, 'SMS_PROVIDER', 'ORANGE')
        sender_id = sender_id or getattr(settings, 'SMS_SENDER_ID', 'EDUCATION')

        # Nettoyage du numéro
        numero = numero.replace(' ', '').strip()
        if not numero.startswith('+'):
            numero = f"+223{numero.lstrip('0')}"

        # Payload API
        payload = {
            "recipient": numero,
            "message": message,
            "sender_id": sender_id,
            "timestamp": datetime.now().isoformat()
        }

        try:
            if provider == 'ORANGE':
                headers = {
                    'Authorization': f'Bearer {settings.ORANGE_API_KEY}',
                    'Content-Type': 'application/json'
                }
                response = requests.post(
                    settings.ORANGE_SMS_URL,
                    json=payload,
                    headers=headers,
                    timeout=10
                )

            elif provider == 'MALITEL':
                headers = {'X-API-KEY': settings.MALITEL_API_KEY}
                response = requests.post(
                    settings.MALITEL_SMS_URL,
                    data=payload,
                    headers=headers,
                    timeout=10
                )

            # Vérification réponse
            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'success'

            logger.error(f"Erreur API SMS: {response.status_code} - {response.text}")
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur connexion API SMS: {str(e)}")
            return False