import os
import logging
import uuid
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.exceptions import ValidationError
from .validators import validate_file_upload

logger = logging.getLogger(__name__)


def save_files_to_temp(request_files, user_id):
    """Sauvegarde sécurisée des fichiers dans un dossier temporaire avec structure de répertoire contrôlée"""
    temp_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'eleve'))
    print(temp_storage)
    saved_files = {}

    try:
        for field_name, file in request_files.items():
            validate_file_upload(file)

            # Génération d'un chemin sécurisé
            ext = os.path.splitext(file.name)[1].lower()
            safe_user_dir = str(user_id).replace("..", "").strip("/")
            unique_filename = f"{safe_user_dir}/{uuid.uuid4().hex}{ext}"

            # Validation supplémentaire du chemin
            if '..' in unique_filename or not unique_filename.startswith(safe_user_dir):
                raise ValidationError("Structure de répertoire invalide")

            saved_name = temp_storage.save(unique_filename, file)
            saved_files[field_name] = saved_name
        return saved_files
    except Exception as e:
        logger.error(f"Erreur sauvegarde temporaire : {e}", exc_info=True)
        # Nettoyage en cas d'erreur
        for f in saved_files.values():
            try:
                temp_storage.delete(f)
            except Exception as del_error:
                logger.error(f"Erreur nettoyage fichier {f}: {del_error}")
        raise


def assign_files_to_user(user_profile, temp_files):
    """Déplacement définitif des fichiers avec vérification de sécurité renforcée"""
    temp_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'eleve'))
    user_dir = str(user_profile.id)

    try:
        for field_name, temp_name in temp_files.items():
            # Validation du chemin et des permissions
            if not temp_name.startswith(user_dir) or '..' in temp_name:
                logger.warning(f"Tentative d'accès non autorisé: {temp_name}")
                continue

            if not temp_storage.exists(temp_name):
                logger.error(f"Fichier temporaire manquant: {temp_name}")
                continue

            # Lecture sécurisée
            with temp_storage.open(temp_name) as f:
                content = ContentFile(f.read())
                content.name = os.path.basename(temp_name)  # Nom original préservé

                # Suppression ancien fichier
                current_file = getattr(user_profile, field_name)
                if current_file:
                    current_file.delete(save=False)

                # Sauvegarde dans le répertoire final
                final_path = os.path.join(user_dir, content.name)
                getattr(user_profile, field_name).save(final_path, content, save=False)

            # Nettoyage du temporaire
            temp_storage.delete(temp_name)

        user_profile.save()
        return True

    except Exception as e:
        logger.critical(f"Erreur migration fichiers: {e}", exc_info=True)
        return False

'''def save_files_to_temp(request_files, user_id):
    """Sauvegarde sécurisée des fichiers dans un dossier temporaire"""
    temp_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'eleve'))
    saved_files = {}

    try:
        for field_name, file in request_files.items():
            # Validation du fichier
            validate_file_upload(file)

            # Génération d'un nom sécurisé
            ext = os.path.splitext(file.name)[1].lower()
            unique_name = f"{user_id}/{uuid.uuid4().hex}{ext}"

            saved_name = temp_storage.save(unique_name, file)
            saved_files[field_name] = saved_name

        return saved_files

    except Exception as e:
        logger.error(f"Erreur sauvegarde fichiers temporaires : {e}", exc_info=True)
        # Nettoyage sécurisé
        for f in saved_files.values():
            try:
                temp_storage.delete(f)
            except Exception as del_error:
                logger.error(f"Erreur suppression fichier {f}: {del_error}")
        raise


def assign_files_to_user(user_profile, temp_files):
    """Déplacement sécurisé des fichiers validés"""
    temp_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'eleve'))

    try:
        for field_name, temp_name in temp_files.items():
            if not hasattr(user_profile, field_name):
                continue

            # Vérification du chemin pour éviter les attaques par traversal
            if not temp_storage.exists(temp_name) or '..' in temp_name:
                logger.warning(f"Tentative d'accès fichier invalide: {temp_name}")
                continue

            with temp_storage.open(temp_name) as f:
                content = ContentFile(f.read())
                content.name = os.path.basename(temp_name).split('_', 2)[-1]

                # Suppression de l'ancien fichier si existe
                current_file = getattr(user_profile, field_name)
                if current_file:
                    current_file.delete(save=False)

                # Sauvegarde sécurisée
                getattr(user_profile, field_name).save(content.name, content, save=False)

            temp_storage.delete(temp_name)

        user_profile.save()
        return True

    except Exception as e:
        logger.critical(f"Erreur assignation fichiers : {e}", exc_info=True)
        return False'''

# if len(os.path.normpath().split(os.sep)) > 3:
#     raise ValidationError("Structure de répertoire invalide")