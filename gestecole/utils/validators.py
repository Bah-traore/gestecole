import magic
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _



def validate_file_upload(file):
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_MIME_TYPES = {
        'image/jpeg': ['jpg', 'jpeg'],
        'image/png': ['png'],
        'application/pdf': ['pdf']
    }

    # Vérification de la taille
    if file.size > MAX_SIZE:
        raise ValidationError(_(f"Fichier trop volumineux (max {MAX_SIZE // 1024 // 1024}MB)"))

    # Vérification réelle du type MIME
    mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)

    if mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(_("Type de fichier non autorisé"))

    # Vérification de l'extension
    ext = file.name.split('.')[-1].lower()
    if ext not in ALLOWED_MIME_TYPES.get(mime, []):
        raise ValidationError(_("Extension de fichier non conforme au type détecté"))