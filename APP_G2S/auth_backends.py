from datetime import timedelta


from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from APP_G2S.models import Administrateur, Eleve, Enseignant


# User = get_user_model()
#
class AdminBackend(ModelBackend):
    def authenticate(self, request, identifiant=None, password=None, **kwargs):
        User = get_user_model()


        try:
            user = Administrateur.objects.get(identifiant=identifiant)
            if user.check_password(password):
                return user
        except Administrateur.DoesNotExist:
            return None


    def get_user(self, user_id):
        try:
            return Administrateur.objects.get(pk=user_id)
        except Administrateur.DoesNotExist:
            return None


class TelephoneBackend(ModelBackend):
    def authenticate(self, request, telephone=None, password=None, last_name=None, **kwargs):

        try:
            # print(telephone)
            userCitoyen = Eleve.objects.get(telephone=telephone)
            print('username in TelephoneBackend:', userCitoyen.last_name)
            if userCitoyen.check_password(password):
                return userCitoyen
        except Exception as e:
            print(e)
            return None

    def get_user(self, user_id):
        try:
            return Eleve.objects.get(pk=user_id)
        except Exception as e:
            return None

class MatriculeBackend(ModelBackend):
    def authenticate(self, request, matricule=None, password=None, **kwargs):
        try:
            user = Enseignant.objects.get(identifiant=matricule)
            if user.check_password(password):
                return user
        except Enseignant.DoesNotExist:
            return None
        except Exception as e:
            print(e)
            return None

    def get_user(self, user_id):
        try:
            return Enseignant.objects.get(pk=user_id)
        except Enseignant.DoesNotExist:
            return None
        except Exception as e:
            print(e)
            return None


class RolePermissionBackend(ModelBackend):
    """
    Backend de permissions basé sur les rôles.

    Ce backend donne automatiquement toutes les permissions aux directeurs,
    et vérifie les permissions spécifiques pour les autres rôles.

    Les permissions sensibles sont définies dans SENSITIVE_PERMISSIONS et
    ne sont accordées qu'aux directeurs.
    """

    # Permissions qui ne sont accordées qu'aux directeurs
    SENSITIVE_PERMISSIONS = [
        'APP_G2S.view_all',
        'APP_G2S.approve_all',
        'APP_G2S.add_administrateur',
        'APP_G2S.change_administrateur',
        'APP_G2S.delete_administrateur',
        'APP_G2S.view_accesslog',
        'APP_G2S.add_accesslog',
        'APP_G2S.change_accesslog',
        'APP_G2S.delete_accesslog',
        'APP_G2S.view_approvalrequest',
        'APP_G2S.add_approvalrequest',
        'APP_G2S.change_approvalrequest',
        'APP_G2S.delete_approvalrequest',
    ]

    # Permissions accordées aux censeurs
    CENSEUR_PERMISSIONS = [
        'APP_G2S.manage_pedagogy',
        'APP_G2S.validate_absences',
        'APP_G2S.view_eleve',
        'APP_G2S.view_classe',
        'APP_G2S.view_matiere',
        'APP_G2S.view_enseignant',
        'APP_G2S.add_eleve',
        'APP_G2S.change_eleve',
        'APP_G2S.add_classe',
        'APP_G2S.change_classe',
        'APP_G2S.add_matiere',
        'APP_G2S.change_matiere',
        'APP_G2S.add_enseignant',
        'APP_G2S.change_enseignant',
    ]

    # Permissions accordées aux surveillants
    SURVEILLANT_PERMISSIONS = [
        'APP_G2S.validate_absences',
        'APP_G2S.view_eleve',
        'APP_G2S.view_classe',
        'APP_G2S.view_absence',
        'APP_G2S.add_absence',
        'APP_G2S.change_absence',
    ]

    # Permissions accordées aux comptables
    COMPTABLE_PERMISSIONS = [
        'APP_G2S.view_paiement',
        'APP_G2S.add_paiement',
        'APP_G2S.change_paiement',
        'APP_G2S.view_eleve',
        'APP_G2S.view_classe',
    ]

    def has_perm(self, user_obj, perm, obj=None):
        # Si l'utilisateur n'est pas un objet User ou n'est pas authentifié, il n'a aucune permission
        if not isinstance(user_obj, (Administrateur, Eleve, Enseignant)) or not hasattr(user_obj, 'role'):
            return False

        # Les directeurs ont toutes les permissions
        if user_obj.role == 'DIRECTEUR':
            return True

        # Les permissions sensibles ne sont accordées qu'aux directeurs
        if perm in self.SENSITIVE_PERMISSIONS:
            return False

        # Vérifier les permissions spécifiques au rôle
        if user_obj.role == 'CENSEUR' and perm in self.CENSEUR_PERMISSIONS:
            return True

        if user_obj.role == 'SURVEILLANT' and perm in self.SURVEILLANT_PERMISSIONS:
            return True

        if user_obj.role == 'COMPTABLE' and perm in self.COMPTABLE_PERMISSIONS:
            return True

        # Vérifier les groupes et permissions standards
        return super().has_perm(user_obj, perm, obj)
