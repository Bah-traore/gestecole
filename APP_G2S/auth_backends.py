from datetime import timedelta


from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from APP_G2S.models import Administrateur, Eleve


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


# class MatriculeBackend(ModelBackend):
#     def authenticate(self, request, matricule=None, password=None, **kwargs):
#         try:
#             agent = Agent.objects.get(matricule=matricule)
#
#             # Vérification du verrouillage
#             if agent.login_attempts >= 5 and agent.last_attempt > timezone.now() - timedelta(hours=1):
#                 raise PermissionDenied("Compte temporairement verrouillé")
#
#             if agent.check_password(password):
#                 agent.login_attempts = 0
#                 agent.save()
#                 return agent
#             else:
#                 agent.login_attempts += 1
#                 agent.last_attempt = timezone.now()
#                 agent.save()
#         except Agent.DoesNotExist:
#             pass
#         return None
#
#
#     def get_user(self, user_id):
#         User = get_user_model()
#         print("User_id dans auth_backends.py :" , user_id)
#         try:
#             return Agent.objects.get(pk=user_id)
#         except User.DoesNotExist:
#             return None



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


class RolePermissionBackend(ModelBackend):
    def has_perm(self, user_obj, perm, obj=None):
        if user_obj.role == 'DIRECTEUR':
            return True

        # Vérifier les groupes et permissions
        return super().has_perm(user_obj, perm, obj)