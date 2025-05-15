import math
import os
import secrets
import tempfile
import shutil
import mimetypes
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import magic
import pyclamd





def generate_secure_code(length=6):
    """Génère un code de sécurité cryptographique"""
    if length < 4 or length > 10:
        raise ValueError("Longueur invalide")
    return secrets.randbelow(10 ** (length))  # Code numérique sécurisé

class TemporaryFileManager:
    """Gère les fichiers temporaires avec nettoyage automatique"""

    def __init__(self, files):
        self.files = files
        self.temp_dir = tempfile.mkdtemp()
        self.saved_paths = {}

    def __enter__(self):
        for field, file in self.files.items():
            # Validation préalable basique
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("Fichier trop volumineux")

            # Création d'un chemin sécurisé
            temp_path = os.path.join(self.temp_dir, secrets.token_hex(8))
            with open(temp_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            self.saved_paths[field] = temp_path
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Nettoyage sécurisé
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def get_files(self):
        return self.saved_paths


def secure_file_validation(file_path):
    """Validation complète des fichiers"""
    # 1. Vérification du type MIME réel
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)

    if file_type not in settings.ALLOWED_FILE_TYPES:
        raise ValidationError(f"Type de fichier non autorisé: {file_type}")

    # 2. Scan antivirus avec ClamAV
    try:
        cd = pyclamd.ClamdUnixSocket()
        scan_result = cd.scan_file(file_path)
        if scan_result:
            raise ValidationError(f"Malware détecté: {scan_result[file_path][1]}")
    except pyclamd.ConnectionError:
        raise RuntimeError("Service antivirus indisponible")

    # 3. Vérification de l'entropie pour détecter les fichiers cryptés
    if calculate_entropy(file_path) > 7.5:
        raise ValidationError("Fichier suspect: entropie trop élevée")


def calculate_entropy(file_path):
    """Calcule l'entropie d'un fichier"""
    with open(file_path, 'rb') as f:
        data = f.read()
    if not data:
        return 0.0
    # Calcul de la fréquence des octets
    frequencies = [0] * 256
    for byte in data:
        frequencies[byte] += 1
    entropy = 0.0
    for freq in frequencies:
        if freq > 0:
            p = freq / len(data)
            entropy -= p * math.log2(p)
    return entropy