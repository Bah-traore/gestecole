from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from APP_G2S.models import Administrateur, Eleve



#
class Super_AgentBackend(ModelBackend):
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

# User = get_user_model()
#
# class AdministrationBackend(ModelBackend):
#     def authenticate(self, request, identifiant=None, password=None, **kwargs):
#         print("mes variables :", identifiant, password)
#         try:
#             user = Administration.objects.get(identifiant=identifiant)
#             print(user)
#             print(password)
#             print(user.password)
#             if check_password(password, user.password):
#                 return user
#         except Administration.DoesNotExist:
#             return None
#
#
#     def get_user(self, user_id):
#         try:
#             return Administration.objects.get(pk=user_id)
#         except Administration.DoesNotExist:
#             return None

class AdministrationBackend(ModelBackend):
    def authenticate(self, request, identifiant=None, password=None, **kwargs):
        try:
            user = Administrateur.objects.get(identifiant=identifiant)
            print("[DEBUG] Utilisateur trouvé :", user)  # Vérifiez si l'utilisateur existe
            if check_password(password, user.password):
                print("[DEBUG] Mot de passe valide")  # Confirmez le succès du check
                return user
            else:
                print("[DEBUG] Mot de passe invalide")  # Identifiez les mots de passe incorrects
        except Administrateur.DoesNotExist:
            print("[DEBUG] Aucun utilisateur avec cet identifiant")  # Log si l'identifiant est inconnu
        return None

class TelephoneBackend(ModelBackend):
    def authenticate(self, request, telephone=None, password=None, last_name=None, **kwargs):

        try:
            # print(telephone)
            userParent = Eleve.objects.get(telephone=telephone)
            print('username in TelephoneBackend:', userParent.last_name)
            if userParent.check_password(password):
                return userParent
        except Exception as e:
            print(e)
            return None

    def get_user(self, user_id):
        try:
            return Eleve.objects.get(pk=user_id)
        except Exception as e:
            return None

