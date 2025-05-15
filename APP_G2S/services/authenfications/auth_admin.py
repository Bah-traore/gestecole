from django.contrib.auth.hashers import check_password
from APP_G2S.models import Administrateur


def login_user_admin(identifiant, password):
    if Administrateur.objects.filter(identifiant=identifiant).exists():
        if check_password(password, Administrateur.objects.get(identifiant=identifiant).password):
            print("le code est correct")
            return Administrateur.objects.get(identifiant=identifiant)
        else:
            print("le code est incorrect 1")
            return None
    print("le identifiant est incorrect 1")
    return None