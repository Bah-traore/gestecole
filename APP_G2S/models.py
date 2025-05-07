import logging
import random
import secrets
import string
from collections import defaultdict
from datetime import timedelta
import pyotp
from celery import shared_task
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from gestecole import settings
from gestecole.utils.calculatrice_bulletin import calculer_moyenne_generale

from gestecole.utils.idgenerateurs import IDGenerator
from gestecole.utils.validators import validate_file_upload

logger = logging.getLogger(__name__)

#
# class Tenant(models.Model):
#     nom = models.CharField(max_length=100, unique=True)
#     subdomain = models.CharField(max_length=50, unique=True)
#     logo = models.ImageField(upload_to='tenants/logo/', null=True, blank=True)
#     config = models.JSONField(default=dict)  # Stocke les paramètres spécifiques
#     is_active = models.BooleanField(default=True)
#     date_creation = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return self.nom



class Enseignant(AbstractUser):
    identifiant = models.CharField(max_length=30, unique=True)
    telephone = PhoneNumberField(region='ML', unique=True)
    nom_complet = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to='enseignant/',
                                        default='default_profile.jpg',
                                        validators=[validate_file_upload]
    )
    matieres = models.ManyToManyField('Matiere', related_name='enseignants')
    # password = models.CharField(max_length=129)
    is_enseignant = models.BooleanField(default=True)
    username = models.CharField(max_length=20, blank=True, verbose_name="Nom d'utilisateur", editable=False)
    email = models.EmailField(editable=False)
    date_joined = models.DateTimeField(auto_created=True, auto_now_add=True, editable=False)
    last_login = models.DateTimeField(auto_created=True, auto_now_add=True, blank=True, editable=False)
    first_name = models.CharField(max_length=20, editable=False)
    last_name = models.CharField(max_length=20, editable=False)
    is_superuser = models.BooleanField(default=False, editable=False)
    is_staff = models.BooleanField(default=False, editable=False)
    is_active = models.BooleanField(default=True, editable=False)


    groups = None
    user_permissions = None

    class Meta:
        verbose_name = 'Enseignant'
        verbose_name_plural = 'Enseignants'

    def __str__(self):
        return self.nom_complet



class Matiere(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    coefficient = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])


    def __str__(self):
        return self.nom

class Classe(models.Model):
    niveau = models.PositiveIntegerField()
    section = models.CharField(max_length=20, choices=[('A', 'Section A'),
        ('B', 'Section B'),
        ('C', 'Section C'),
        ], default='A')
    matieres = models.ManyToManyField(Matiere, verbose_name='Matiere')

    responsable = models.ForeignKey('Enseignant', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.niveau} - {self.section}"



class EleveManager(BaseUserManager):  # Remplacer models.Manager par BaseUserManager
    def create_user(self, telephone, password, **extra_fields):
        if not telephone:
            raise ValueError("Le numéro de téléphone est requis")
        user = self.model(
            telephone=telephone,
            **extra_fields
        )
        user.set_password(password)  # Utiliser set_password au lieu de make_password
        user.save(using=self._db)
        return user


class PeriodeManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)

class Periode(models.Model):

    numero = models.PositiveSmallIntegerField()
    annee_scolaire = models.CharField(max_length=22)
    classe = models.ManyToManyField(Classe, verbose_name='Classe')
    date_debut = models.DateField()
    date_fin = models.DateField()
    is_active = models.BooleanField("Période active", default=False)
    cloture = models.BooleanField(default=False)
    objects = PeriodeManager()

    class Meta:
        constraints = [
            # models.UniqueConstraint(
            #     fields=['classe', 'annee_scolaire'],
            #     name='unique_annee_classe'
            # ),
            models.CheckConstraint(
                check=models.Q(date_fin__gt=models.F('date_debut')),
                name='check_dates_ordre'
            )
        ]

    def clean(self):
        super().clean()

        # Vérification des chevauchements de dates
        conflits = Periode.objects.filter(
            classe=self.classe,
            annee_scolaire=self.annee_scolaire,
            date_debut__lt=self.date_fin,
            date_fin__gt=self.date_debut
        ).exclude(pk=self.pk)

        if conflits.exists():
            raise ValidationError(
                "Une période existe déjà pour cette classe et cette année scolaire avec des dates qui se chevauchent")

    def notes_valides(self):
        return self.note_set.filter(est_valide=True)

    def __str__(self):
        return f"{self.numero} ({self.annee_scolaire})"

class Eleve(AbstractUser):
    identifiant = models.CharField(max_length=20, unique=True, null=True, blank=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    prenom_parent = models.CharField(max_length=100)
    nom_parent = models.CharField(max_length=100)
    telephone = PhoneNumberField(db_index=True, region='ML')
    profile_picture = models.ImageField(upload_to='eleves/',
                                        default='default_profile.jpg',
                                        validators=[validate_file_upload])
    age = models.PositiveSmallIntegerField()
    residence = models.CharField(max_length=50)
    is_eleve = models.BooleanField(default=True, verbose_name="Un élève")
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='eleves')
    username = models.CharField(max_length=20, blank=True, verbose_name="Nom d'utilisateur", editable=False)
    last_login = models.DateTimeField(auto_now_add=True, auto_created=True, blank=True, editable=False)
    first_name = models.CharField(max_length=20, editable=False)
    last_name = models.CharField(max_length=20, editable=False)
    date = models.DateTimeField(auto_now_add=True)
    date_joined = models.DateTimeField(auto_created=True, auto_now_add=True, editable=False)
    password = models.CharField(max_length=128, verbose_name="Mot de Passe")
    code_expiry = models.DateTimeField(default=timezone.now() + timedelta(minutes=int(settings.SMS_CODE_VALIDITY)), editable=True, help_text="Elle s'auto saisie")
    sms_code = models.CharField(max_length=6, blank=True, editable=False)
    email = models.EmailField(editable=False)
    user_type = models.CharField(max_length=20, default='eleve', editable=False)
    is_superuser = models.BooleanField(default=False, editable=False)
    is_staff = models.BooleanField(default=False, editable=False)
    is_active = models.BooleanField(default=True, editable=False)
    suspendu = models.BooleanField(default=False, verbose_name="Suspendu pour impayés")

    def envoyer_sms_parent(self, message, force=False):
        """
        Envoie un SMS au parent/tuteur de l'élève
        Args:
            message (str): Le contenu du message (max 160 caractères)
            force (bool): Envoyer même si l'élève est suspendu ou désactivé
        Returns:
            bool: True si réussi, False si échec
        """
        if not self.is_active and not force:
            return False

        from gestecole.utils.idgenerateurs import SMSService  # Import local pour éviter les imports circulaires
        from django.conf import settings

        # Validation du numéro
        if not self.telephone:
            logger.error(f"Aucun numéro pour l'élève {self.get_full_name()}")
            return False

        # Formatage du message
        message = f"[ECOLE {settings.ECOLE_NOM}] {message.strip()}"
        if len(message) > 160:
            message = message[:157] + "..."  # Tronquer tout en gardant le sens

        try:
            # Envoi via le service SMS
            success = SMSService.send_sms(
                numero=str(self.telephone),
                message=message,
                sender_id=settings.SMS_SENDER_ID
            )

            # Journalisation
            if success:
                logger.info(f"SMS envoyé à {self.telephone} pour {self.get_full_name()}")
            else:
                logger.warning(f"Échec envoi SMS à {self.telephone}")

            return success

        except Exception as e:
            logger.error(f"Erreur envoi SMS pour {self.id}: {str(e)}")
            return False


    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groupes',
        blank=True,
        help_text='Groupes auxquels cet utilisateur appartient.',
        editable=False
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='permissions',
        blank=True,
        help_text='Permissions spécifiques à cet utilisateur.',
        editable=False
    )

    def generate_password(self):
        characters = string.digits  # Mot de passe numérique uniquement
        return ''.join(random.choice(characters) for _ in range(6))

    def save(self, *args, **kwargs):
        if not self.identifiant:
            self.identifiant = IDGenerator.generate_student_id(self.classe)
        if not self.password or self.password.startswith('pbkdf2_sha256') is False:
            temp_password = self.generate_password()
            self.set_password(temp_password)
            self.sms_code = temp_password  # Stocker le mot de passe temporaire
            self.code_expiry = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)


    class Meta:
        verbose_name = 'Elève'
        verbose_name_plural = 'Elèves'
        permissions = [
            ('view_own_data', 'Peut voir ses propres données'),
        ]


    objects = EleveManager()

    def __str__(self):
        return str(self.prenom) + '-' + str(self.nom)

class EmploiDuTemps(models.Model):
    RECURRENCE_CHOICES = [
        ('PONCTUEL', 'Ponctuel'),
        ('HEBDOMADAIRE', 'Toutes les semaines'),
        ('MENSUEL', 'Tous les mois'),
    ]

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='emplois_du_temps')
    enseignant = models.ForeignKey(Enseignant, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Date du cours")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")
    salle = models.CharField(max_length=50, blank=True, null=True)
    recurrence = models.CharField(
        max_length=12,
        choices=RECURRENCE_CHOICES,
        default='PONCTUEL'
    )
    recurrence_end = models.DateField(null=True, blank=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.matiere} - {self.classe} | {self.date} ({self.start_time}-{self.end_time})"

    def clean(self):
        # Validation des conflits
        conflits = EmploiDuTemps.objects.filter(
            models.Q(enseignant=self.enseignant) | models.Q(classe=self.classe),
            date=self.date,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(pk=self.pk)

        if conflits.exists():
            raise ValidationError("Conflit d'horaire détecté pour l'enseignant ou la classe")

    class Meta:
        verbose_name = "Emploi du temps"
        verbose_name_plural = "Emplois du temps"
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name="end_time_after_start_time"
            )
        ]

class Examen(models.Model):
    CHOICE_ = [
        ('EN_COURS', 'en_cours'),
        ('FIN', 'fin')
    ]
    nom = models.CharField("Nom de l'examen", max_length=100)
    date = models.DateField("Date de l'examen")
    date_fin = models.DateField("Date de fin")
    classe = models.ManyToManyField(Classe, verbose_name="Classe")
    matieres = models.ManyToManyField(Matiere, verbose_name="Matière")
    validite = models.CharField(max_length=20, choices=CHOICE_)
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE, null=True)

    def clean(self):
        super().clean()

        # Vérification des champs obligatoires
        if not all([self.periode, self.date, self.date_fin]):
            raise ValidationError("Les champs 'date', 'date_fin' et 'periode' sont obligatoires.")

        # Validation 1 : L'examen doit être entièrement dans la période
        if (self.date < self.periode.date_debut) or (self.date_fin > self.periode.date_fin):
            raise ValidationError(
                "Les dates de l'examen doivent être comprises entre "
                f"{self.periode.date_debut} et {self.periode.date_fin}."
            )

        # Validation 2 : Cohérence date début/fin
        if self.date_fin < self.date:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")
        if self.date_fin >= timezone.now():
            self.validite = "FIN"
            raise ValidationError(f"{self.nom} - du {self.date} au {self.date_fin} à eteint sa date de fin")
    def save(self, *args, **kwargs):
        if self.date_fin < timezone.now().date():
            self.validite = 'FIN'
        self.full_clean()
        super().save(*args, **kwargs)

    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=['date', 'classe'],
    #             name='unique_examen_date_classe'
    #         )
    #     ]

    def __str__(self):
        return f"{self.nom} - ({self.date})"

class Note(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes_de_classe')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    # emploi_du_temps = models.ForeignKey(EmploiDuTemps, on_delete=models.CASCADE, blank=True)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    valeur = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(20.0)])
    date = models.DateField()
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE, null=True)
    examen_reference = models.ForeignKey(Examen, on_delete=models.SET_NULL, null=True, blank=True)



    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=['eleve', 'matiere'],  # Devenu singulier
    #             name='unique_note_par_matiere'
    #         )
    #     ]

    def clean(self):
        super().clean()

        # Validation 1 : Cohérence période/matière
        # if self.periode and self.classe.classe != self.periode.classe:
        #     raise ValidationError("La matière ne correspond pas à la classe de la période")

        # Validation 2 : Date dans la période
        if self.date and (self.date < self.periode.date_debut or self.date > self.periode.date_fin):
            raise ValidationError("La date de la note est en dehors de la période scolaire")

    def __str__(self):
        return f"{self.eleve} - {self.classe} : {self.valeur}"


class NoteExamen(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes_examen')
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    note = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(40.0)],
        verbose_name="Note"
    )
    date = models.DateField()  # Suppression de auto_now=True
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE)
    est_valide = models.BooleanField(default=False)

    def clean(self):
        super().clean()

        # Validation 1 : Date dans une période active
        if self.date:
            periode_active = Periode.objects.filter(
                is_active=True,
                date_debut__lte=self.date,
                date_fin__gte=self.date
            ).first()

            if not periode_active:
                raise ValidationError("La date n'appartient à aucune période active")

            self.periode = periode_active

        # Validation 2 : Pas de modification après clôture
        if self.pk and self.periode and self.periode.cloture:
            raise ValidationError("Impossible de modifier une note d'une période clôturée")

        # # Validation 3 : Cohérence matière/classe
        # if self.matiere.classe != self.eleve.classe:
        #     raise ValidationError("La matière ne correspond pas à la classe de l'élève")

    def save(self, *args, **kwargs):
        # Marquer comme valide si toutes les conditions sont remplies
        try:
            self.full_clean()
            self.est_valide = True
        except ValidationError:
            self.est_valide = False

        if not self.periode:
            self.periode = self.examen.periode
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['eleve', 'matiere', 'periode'],
                name='unique_note_par_matiere_periode'
            )
        ]

    def __str__(self):
        return f"{self.eleve} - {self.examen} : {self.note}"


class Absence(models.Model):
    JUSTIFICATION_STATUS = [
        ('NON_JUSTIFIE', 'Non justifié'),
        ('EN_ATTENTE', 'En attente de validation'),
        ('JUSTIFIE', 'Justifié'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='absences')
    date = models.DateField()
    motif = models.TextField(blank=True, null=True)
    emploi_du_temps = models.ForeignKey(EmploiDuTemps, on_delete=models.CASCADE)

    justification_status = models.CharField(
        max_length=20,
        choices=JUSTIFICATION_STATUS,
        default='NON_JUSTIFIE'
    )
    justification_document = models.FileField(
        upload_to='justificatifs/',
        null=True,
        blank=True,
        validators=[validate_file_upload]
    )
    justification_commentaire = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.date = self.emploi_du_temps.date  # Synchronisation automatique
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Absence de {self.eleve} le {self.date}"


class Administrateur(AbstractUser):

    CHOICE_ROLE = [
        ('DIRECTEUR', 'directeur'),
        ('CENSEUR', 'censeur'),
        ('SURVEILLANT', 'surveillant'),
        ('COMPTABLE', 'comptable'),

    ]

    role = models.CharField(max_length=20, choices=CHOICE_ROLE)

    telephone = PhoneNumberField(unique=True, null=True, region='ML')
    email = models.EmailField(max_length=255, unique=True)
    identifiant = models.CharField(max_length=20, unique=True, null=True)
    prenom = models.CharField(max_length=20)
    nom = models.CharField(max_length=20)
    username = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Nom d'utilisateur", editable=False)
    last_login = models.DateTimeField(auto_now_add=True, auto_created=True, blank=True, editable=False)
    date_joined = models.DateTimeField(auto_now_add=True, auto_created=True, blank=True, editable=False)
    first_name = models.CharField(max_length=20, editable=False)
    last_name = models.CharField(max_length=20, editable=False)
    password = models.CharField(max_length=128, verbose_name="Mot de Passe")
    is_staff = models.BooleanField(default=False, editable=False)
    classe_creer = models.ManyToManyField('classe', related_name='administration', blank=True)
    eleve_creer = models.ManyToManyField('eleve', related_name='administration', blank=True)
    enseignant_creer = models.ManyToManyField('enseignant', related_name='administration', blank=True)
    matiere_creer = models.ManyToManyField('Matiere', related_name='administration', blank=True)


    is_superuser = models.BooleanField(default=False, editable=False)
    is_admin = models.BooleanField(default=True, verbose_name="Compte admin")

    USERNAME_FIELD = 'identifiant'
    REQUIRED_FIELDS = ['nom', 'prenom', 'telephone']

    class Meta:
        verbose_name = 'Administrateur'
        verbose_name_plural = 'Administrateurs'
        permissions = [
            ('view_all', 'Peut voir toutes les données'),
            ('approve_all', 'Peut approuver toutes les actions'),
            ('manage_pedagogy', 'Gère la pédagogie'),
            ('validate_absences', 'Valider les absences'),
            # Ajouter toutes les permissions de HIERARCHY
        ]

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groupes',
        blank=True,
        help_text='Groupes auxquels cet utilisateur appartient.',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='permissions',
        blank=True,
        help_text='Permissions spécifiques à cet utilisateur.',
    )

    def save(self, *args, **kwargs):
        if self.password.startswith('pbkdf2_sha1') is False:
            # print('interieurs',self.password.startswith('pbkdf2_sha1') is False,  self.password, type(self.password))
            if self.pk is None or self.password:
                self.set_password(self.password)
            super().save(*args, **kwargs)
        # else:
        #     super().save(*args, **kwargs)

    def set_password(self, raw_password):
        # print(self.password, type(self.password))
        self.password = make_password(raw_password)
        # print(self.password, type(self.password))


    # def ajouter_enseignant(self, enseignant):
    #
    #     """Ajoute un agent au super agent."""
    #
    #     self.enseignant_creer.add(enseignant)    #
    # #
    # #
    # # def desactiver_agent(self, agent):
    # #
    # #     """Désactive un agent."""
    # #
    # #     agent.is_active = False
    # #
    # #     agent.save()
    # #
    # #
    # #
    # # def activer_agent(self, agent):
    # #
    # #     """Active un agent."""
    # #
    # #     agent.is_active = True
    # #
    # #     agent.save()





@receiver(pre_save, sender=EmploiDuTemps)
def validate_emploi_du_temps(sender, instance, **kwargs):
    instance.full_clean()

@shared_task
def generer_recurrence_emploi(pk):
    instance = EmploiDuTemps.objects.get(pk=pk)
    if instance.recurrence != 'PONCTUEL':
        current_date = instance.date
        while current_date <= instance.recurrence_end:
            current_date += timedelta(
                weeks=1 if instance.recurrence == 'HEBDOMADAIRE' else 30
            )
            EmploiDuTemps.objects.create(
                **{field.name: getattr(instance, field.name) for field in instance._meta.fields if field.name not in ['id', 'recurrence_end']},
                date=current_date
            )


class BulletinPerformance(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='bulletins')
    classes = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='bulletins')
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE)
    date_creation = models.DateField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    versions = models.JSONField(default=list)  # Pour garder un historique
    moyenne_coefficient = models.FloatField(default=0.0)
    moyenne_generale = models.FloatField(default=0.0)
    appreciation = models.TextField(blank=True, null=True)
    classement = models.PositiveIntegerField(blank=True, null=True)

    def calculer_moyenne_generale(self):
        bulletin_matieres = self.matieres.all()

        moyennes_coefficient = defaultdict(float)
        for bm in bulletin_matieres:
            moyennes_coefficient[bm.matiere.id] += bm.note * bm.matiere.coefficient

        print('moyenne_coeff', dict(moyennes_coefficient))
        matieres_classe = Matiere.objects.filter(classe=self.eleve.classe)
        self.moyenne_generale = calculer_moyenne_generale(moyennes_coefficient, matieres_classe)

    # def save(self, *args, **kwargs):
    #     # Calculer la moyenne avant la sauvegarde
    #     # Éviter la récursion avec update_fields *********
    #     self.calculer_moyenne_generale()
    #     if self.pk is None:
    #         super().save(*args, **kwargs)
    #
    #     # Mettre à jour les champs sans déclencher de récursion
    #     # super().save(update_fields=['moyenne_generale', 'classement'], *args, **kwargs)
    #     # Mise à jour du classement
    #     # super().save(*args, **kwargs)
    #     bulletins = BulletinPerformance.objects.filter(
    #         eleve__classe=self.eleve.classe,
    #         periode=self.periode
    #     ).order_by('-moyenne_generale')
    #
    #     rank = 1
    #     previous_score = None
    #     for idx, bulletin in enumerate(bulletins, start=1):
    #         if bulletin.moyenne_generale != previous_score:
    #             rank = idx
    #             previous_score = bulletin.moyenne_generale
    #         if bulletin.pk == self.pk:
    #             self.classement = rank
    #         BulletinPerformance.objects.filter(pk=bulletin.pk).update(classement=rank)

    def save(self, *args, **kwargs):
        # Sauvegarder d'abord si c'est une nouvelle instance pour obtenir un PK
        if self.pk is None:
            super().save(*args, **kwargs)

        # Calculer la moyenne générale
        self.calculer_moyenne_generale()

        # Mise à jour du classement
        bulletins = BulletinPerformance.objects.filter(
            eleve__classe=self.eleve.classe,
            periode=self.periode
        ).order_by('-moyenne_generale')

        rank = 1
        previous_score = None
        for idx, bulletin in enumerate(bulletins, start=1):
            if bulletin.moyenne_generale != previous_score:
                rank = idx
                previous_score = bulletin.moyenne_generale
            if bulletin.pk == self.pk:
                self.classement = rank
            BulletinPerformance.objects.filter(pk=bulletin.pk).update(classement=rank)

        # Sauvegarder les champs mis à jour
        # super().save(update_fields=['moyenne_generale', 'classement'], *args, **kwargs)




    class Meta:
        unique_together = ('eleve', 'periode')
        verbose_name = "Bulletin de performance"
        verbose_name_plural = "Bulletins de performance"

    def get_notes_details(self):
        # Récupérer les détails des notes avec les coefficients
        notes = Note.objects.filter(eleve=self.eleve).select_related('matiere')
        details = []
        for note in notes:
            details.append({
                'matiere': note.matiere.nom,
                'note': note.valeur,
                'coefficient': note.matiere.coefficient,
                'note_ponderee': note.valeur * note.matiere.coefficient
            })
        return details

    def __str__(self):
        return f"Bulletin de {self.eleve} - {self.date_creation}"

class BulletinMatiere(models.Model):
    bulletin = models.ForeignKey(BulletinPerformance, on_delete=models.CASCADE, related_name='matiere')
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    note = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)]
    )
    class Meta:
        unique_together = ('bulletin', 'matiere')



class PeriodePaiement(models.Model):
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE)
    nom = models.CharField(max_length=50)
    date_debut = models.DateField()
    date_fin = models.DateField()
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)


class Paiement(models.Model):
    MODE_CHOICES = [
        ('ORANGE', 'Orange Money'),
        ('MALITEL', 'M-Money'),
        ('ESPECES', 'Espèces')
    ]

    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('REUSSI', 'Paiement réussi'),
        ('ECHOUE', 'Paiement échoué'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='paiements')
    periode = models.ForeignKey(PeriodePaiement, on_delete=models.CASCADE)
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2)
    date_paiement = models.DateTimeField(auto_now_add=True)
    mode_paiement = models.CharField(max_length=10, choices=MODE_CHOICES)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    statut = models.BooleanField(default=False)
    statut_paiement = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    suspendu = models.BooleanField(default=False)

    def save(self, *args,**kwargs):
        if self.mode_paiement == 'ESPECES' and not self.transaction_id:
            self.transaction_id = f"ESPECES-{timezone.now().timestamp()}"
        super().save(*args, **kwargs)


class AccessLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100)
    url = models.CharField(max_length=500)
    details = models.JSONField(default=dict)
    status = models.CharField(max_length=20)

    @classmethod
    def log(cls, request, action, details=None, status='success'):
        cls.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            url=request.get_full_path(),
            details=details or {},
            status=status
        )


class ApprovalRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvé'),
        ('REJECTED', 'Rejeté')
    ]

    requester = models.ForeignKey(settings.AUTH_USER_MODEL,
                                  related_name='requests_created',
                                  on_delete=models.CASCADE)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 related_name='requests_to_approve',
                                 null=True,
                                 on_delete=models.SET_NULL)
    action_type = models.CharField(max_length=50)
    target_object = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)
    comments = models.TextField(blank=True)

    def approve(self, approver):
        self.status = 'APPROVED'
        self.approver = approver
        self.resolved_at = timezone.now()
        self.save()
        self.execute_action()

    def reject(self, approver, reason):
        self.status = 'REJECTED'
        self.approver = approver
        self.comments = reason
        self.resolved_at = timezone.now()
        self.save()

    def execute_action(self):
        # Implémenter la logique métier selon action_type
        pass


#
# class Agent(AbstractUser):
#     agent_super = models.ManyToManyField(Administrateur, related_name='Agent_super', blank=True)
#     matricule = models.CharField(max_length=20, unique=True, null=True)
#     telephone = PhoneNumberField(db_index=True, unique=True, region='ML')
#     email = models.EmailField(max_length=20, unique=True)
#     prenom = models.CharField(max_length=20)
#     nom = models.CharField(max_length=20)
#     username = models.CharField(max_length=20, blank=True, verbose_name="Nom d'utilisateur")
#     last_login = models.DateTimeField(auto_now_add=True, auto_created=True, blank=True, editable=True)
#     first_name = models.CharField(max_length=20,  editable=True)
#     last_name = models.CharField(max_length=20, editable=True)
#     profile_picture = models.ImageField(upload_to='profiles/', default='default_profile.jpg')
#     password = models.CharField(max_length=128, verbose_name="Mot de Passe")
#
#     code_expiry = models.DateTimeField(default=timezone.now() + timedelta(minutes=int(settings.SMS_CODE_VALIDITY)),
#                                        editable=True, help_text="Elle s'auto saisie")
#
#     is_agent = models.BooleanField(default=True, verbose_name="Un agent")
#     is_active = models.BooleanField(default=True, verbose_name="Compte actif")
#     is_staff = models.BooleanField(default=False, editable=True)
#     super_agent = models.ForeignKey(Administrateur, on_delete=models.CASCADE, null=True, verbose_name="Super Agent responsable")
#     date_joined = models.DateTimeField(auto_now_add=True)
#     login_attempts = models.PositiveIntegerField(default=0)
#     last_attempt = models.DateTimeField(auto_created=True, auto_now_add=True, null=True)
#
#     sms_code = models.CharField(max_length=6, blank=True)
#
#     groups = models.ManyToManyField(
#         'auth.group',
#         verbose_name='groupes',
#         blank=True,
#         help_text='Groupes auxquels cet utilisateur appartient.',
#         # related_name='Agent_groupes'
#     )
#     user_permissions = models.ManyToManyField(
#         'auth.Permission',
#         verbose_name='permissions',
#         help_text='Permissions spécifiques à cet utilisateur.',
#         # related_name='Agent_permissions'
#
#     )
#
#     def save(self, *args, **kwargs):
#         print(self.password.split('_')[0])
#         if self.password.split('_')[0] == 'pbkdf2':
#             super().save(*args, **kwargs)
#             return True
#         if self.pk is None or self.password:
#             self.set_password(self.password)
#         super().save(*args, **kwargs)
#
#     def set_password(self, raw_password):
#         self.password = make_password(raw_password)
#
#
#     class Meta:
#         verbose_name = 'Agent'
#         verbose_name_plural = 'Agents'
#
#
