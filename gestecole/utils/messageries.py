import os
import requests
from urllib.parse import urlencode
from typing import Tuple
import logging
import re
from functools import lru_cache
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()


class SmsOrangeService:
    def __init__(self):
        # Clés API depuis variables d'environnement en français
        self.id_client_orange = os.getenv('ID_CLIENT_ORANGE')
        self.secret_client_orange = os.getenv('SECRET_CLIENT_ORANGE')
        self.jeton_acces_orange = os.getenv('JETON_ACCES_ORANGE')

    def valider_numero_telephone(self, numero: str) -> bool:
        """Valide le format des numéros maliens (+223 followed by 8 digits)"""
        pattern = r'^\+223\d{8}$'
        return bool(re.match(pattern, numero))

    def nettoyer_message(self, message: str) -> str:
        """Nettoie le message pour éviter les injections"""
        # Limite à 160 caractères pour SMS standard
        return message[:160].strip()

    @lru_cache(maxsize=128)
    def obtenir_jeton_acces_orange(self) -> str:
        """Obtient un jeton d'accès pour l'API Orange"""
        url_auth = "https://api.orange.com/oauth/v3/token "

        headers = {
            "Authorization": f"Basic {self.id_client_orange}:{self.secret_client_orange}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(url_auth, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur d'authentification Orange: {str(e)}")
            raise

    def envoyer_sms_orange(self, destinataire: str, message: str) -> Tuple[bool, str]:
        """Envoie un SMS via l'API Orange Mali"""
        if not self.valider_numero_telephone(destinataire):
            return False, "Numéro de téléphone invalide"

        message_nettoye = self.nettoyer_message(message)

        url_envoi = "https://api.orange.com/smsmessaging/v1/outbound/shortcode "

        headers = {
            "Authorization": f"Bearer {self.obtenir_jeton_acces_orange()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "outboundSMSMessageRequest": {
                "address": destinataire,
                "outboundSMSTextMessage": {
                    "message": message_nettoye
                }
            }
        }

        try:
            response = requests.post(url_envoi, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return True, "Message envoyé avec succès via Orange"
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur API Orange: {str(e)}")
            return False, f"Échec d'envoi Orange: {str(e)}"


# Exemple d'utilisation
if __name__ == "__main__":
    service_sms = SmsOrangeService()

    # Exemple d'envoi via Orange
    succes, resultat = service_sms.envoyer_sms_orange(
        "+22365432101",
        "Bonjour, ceci est un test de messagerie sécurisée."
    )

    print(f"Statut: {'Succès' if succes else 'Échec'} - {resultat}")