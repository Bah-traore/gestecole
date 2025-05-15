import random
import string

from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from APP_G2S.models import Eleve, Administrateur, Enseignant
from django.db import transaction
from gestecole.utils.idgenerateurs import IDGenerator
class MyLogin:
    def login_user(self, telephone, password):
        """
        Authentifie un élève par son numéro de téléphone et son mot de passe.
        """
        if Eleve.objects.filter(telephone=telephone).exists():
            if check_password(password, Eleve.objects.get(telephone=telephone).password):
                return Eleve.objects.get(telephone=telephone)
            else:
                return None
                # raise ValidationError("Telephone inconnu")
        return None

    def login_user_Admin(self, identifiant, password):
        """
        Authentifie un administrateur par son identifiant et son mot de passe.
        """
        if Administrateur.objects.filter(identifiant=identifiant).exists():
            if check_password(password, Administrateur.objects.get(identifiant=identifiant).password):
                return Administrateur.objects.get(identifiant=identifiant)
            else:
                return None
        return None

    def login_user_Agent(self, matricule, password):
        """
        Authentifie un enseignant par son identifiant (matricule) et son mot de passe.
        """
        if Enseignant.objects.filter(identifiant=matricule).exists():
            if check_password(password, Enseignant.objects.get(identifiant=matricule).password):
                return Enseignant.objects.get(identifiant=matricule)
            else:
                return None
        return None


class EnseignantCreationService:
    def __init__(self, administrateur, data):
        self.Administrateur = administrateur
        self.data = data.copy()



    @transaction.atomic
    def execute(self):
        self._validate_quota()
        self._validate_data()
        if Enseignant.objects.filter(identifiant=self.data['identifiant']).exists():
            raise ValidationError("Cet enseignant existe déjà")
        if Administrateur.objects.filter(telephone=self.data['telephone']).exists():
            raise ValidationError("Ce numéro de téléphone existe déjà")
        if 'identifiant' not in self.data or not self.data['identifiant']:
            self.data['identifiant'] = IDGenerator.generate_teacher_id()
        # if Administrateur.objects.filter(email=self.data['email']).exists():
        #     raise ValidationError("Cet email existe déjà")
        if 'password' not in self.data:
            self.data['password'] = self.generatriceMDP_default()

        enseignant = self._create_enseignant()
        self._send_credentials(enseignant)
        return enseignant


    def _validate_quota(self):
        if self.Administrateur.enseignant_creer.count() >= 10:
            raise ValidationError("Quota maximum d'agents (10) atteint")

    def _validate_data(self):
        required_fields = ['identifiant', 'telephone']
        for field in required_fields:
            if not self.data.get(field):
                raise ValidationError(f"Le champ {field} est obligatoire")

    def _create_enseignant(self):
        return Administrateur.objects.create(
            administrateur=self.Administrateur,
            identifiant=self.data['identifiant'],
            telephone=self.data['telephone'],
            nom=self.data['nom'],
            prenom=self.data['prenom'],
            # password=make_password(self.data['password']),
            # prenom=self.data.get('prenom', ''),
            # nom=self.data.get('nom', ''),
            # email=self.data.get('email', ''),
            is_active=True
        )

    def generatriceMDP_default(self, longueur=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(characters) for _ in range(longueur))

    def _send_credentials(self, agent):
        prenom = self.data.get('prenom')
        nom = self.data.get('nom')
        identifiant = self.data['identifiant']
        # password = self.data['password']
        telephone = self.data['telephone']
        # email = self.data.get('email')

        if telephone:
            print(f"Agent {nom} {prenom} au matricule: {identifiant}\n Recevez votre Mot de passe: -vide, vous pouvez la changer une fois connecter."
                  f"GOUVERNEMENT DU MALI")



def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
