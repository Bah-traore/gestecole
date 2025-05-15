import logging
import random
import secrets
import string
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

import pyotp
from celery import shared_task
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.aggregates import Sum, Avg
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from gestecole import settings
from gestecole.utils.calculatrice_bulletin import calculer_moyenne_generale

from gestecole.utils.idgenerateurs import IDGenerator
from gestecole.utils.validators import validate_file_upload


logger = logging.getLogger(__name__)

class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)

class TenantManager(models.Manager):
    def get_queryset(self):
        # On suppose que le tenant courant est injecté dans le thread local (middleware)
        from gestecole.utils.tenant import get_current_tenant
        tenant = get_current_tenant()
        qs = super().get_queryset()
        if tenant:
            return qs.filter(tenant=tenant)
        return qs

class Tenant(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    subdomain = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to='tenants/logo/', null=True, blank=True)
    config = models.JSONField(default=dict)  # Stocke les paramètres spécifiques
    is_active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    # Paramètres spécifiques à l'école
    adresse = models.CharField(max_length=255, blank=True)
    telephone = PhoneNumberField(region='ML', null=True, blank=True)
    email = models.EmailField(blank=True)
    site_web = models.URLField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'École'
        verbose_name_plural = 'Écoles'

    def __str__(self):
        return self.nom



class Enseignant(AbstractUser):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, related_name='enseignants')
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

    objects = TenantManager()

    class Meta:
        verbose_name = 'Enseignant'
        verbose_name_plural = 'Enseignants'

    def __str__(self):
        return self.nom_complet



class Matiere(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, related_name='matieres')
    nom = models.CharField(max_length=100)
    coefficient = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    objects = TenantManager()

    class Meta:
        unique_together = ('tenant', 'nom')


    def __str__(self):
        return self.nom



class Classe(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, related_name='classes')
    niveau = models.PositiveIntegerField()
    responsable = models.ForeignKey('Enseignant', on_delete=models.CASCADE, null=True, blank=True)
    section = models.CharField(max_length=1, choices=[('A','A'), ('B','B'), ('C','C')])
    niveau_superieur = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    matieres = models.ManyToManyField('Matiere')

    objects = TenantManager()

    class Meta:
        unique_together = ('tenant', 'niveau', 'section')

    def clean(self):
        if self.niveau_superieur:
            if self.niveau_superieur.niveau <= self.niveau:
                raise ValidationError("Le niveau supérieur doit être plus élevé")
            if self.niveau_superieur.section != self.section:
                raise ValidationError("La section doit rester identique")


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
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, related_name='periodes')
    numero = models.PositiveSmallIntegerField()
    annee_scolaire = models.CharField(max_length=22)
    classe = models.ManyToManyField(Classe, verbose_name='Classe')
    date_debut = models.DateField()
    date_fin = models.DateField()
    is_active = models.BooleanField("Période active", default=False)
    cloture = models.BooleanField(default=False)

    objects = TenantManager()

    @classmethod
    def periode_active(cls):
        return cls.objects.filter(cloture=False).latest('date_fin')

    def __str__(self):
        return f"{self.annee_scolaire} ({'Clôturée' if self.cloture else 'Active'})"

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


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        # Vérification des chevauchements de dates
        # On ne peut pas accéder à self.classe avant que l'objet soit sauvegardé
        # car c'est une relation ManyToMany
        if self.pk:  # Seulement si l'objet a déjà été sauvegardé
            conflits = Periode.objects.filter(
                classe__in=self.classe.all(),
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
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, related_name='eleves')
    identifiant = models.CharField(max_length=20, null=True, blank=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    prenom_pere = models.CharField(max_length=100)
    nom_pere = models.CharField(max_length=100)
    nom_mere = models.CharField(max_length=100)
    prenom_mere = models.CharField(max_length=100)
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
    redoublements = models.PositiveIntegerField(default=0)
    est_expulse = models.BooleanField(default=False)
    historique = models.ManyToManyField(Periode, through='HistoriqueAcademique')


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

    objects = TenantManager()

    def generate_password(self):
        characters = string.digits  # Mot de passe numérique uniquement
        return ''.join(random.choice(characters) for _ in range(6))

    def save(self, *args, **kwargs):
        if not self.identifiant:
            self.identifiant = IDGenerator.generate_student_id(self.classe)
            print('SUCCESS: IDENTIFIANT ELEVE: ', self.identifiant)

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
        unique_together = ('tenant', 'identifiant')


    objects = EleveManager()

    def generer_decision_academique(self):
        bulletins = self.bulletins.filter(periode=Periode.objects.active().first())
        moyenne = bulletins.aggregate(Avg('moyenne_generale'))['moyenne_generale__avg']

        if self.verifier_conditions_promotion():
            if self.classe.niveau_superieur:
                self.classe = self.classe.niveau_superieur
                self.redoublements = 0
                decision = 'ADMIS'
            else:
                decision = 'TERMINE'
        else:
            self.redoublements += 1
            decision = 'REDOUBLE' if self.redoublements < 2 else 'EXPULSE'

        HistoriqueAcademique.objects.create(
            eleve=self,
            periode=Periode.objects.active().first(),
            moyenne=moyenne,
            decision=decision,
            paiement_complet=self.paiements.filter(statut_paiement='REUSSI').exists()
        )

    def verifier_conditions_promotion(self):
        """Vérifie automatiquement les conditions de promotion"""
        # Vérifier les 3 moyennes générales
        bulletins = BulletinPerformance.objects.filter(eleve=self)
        if bulletins.count() < 3:
            return False

        moyennes_valides = all(b.moyenne_generale >= 30 for b in bulletins)

        # Vérifier paiement première tranche
        paiement_ok = Paiement.objects.filter(
            eleve=self,
            tranche__ordre=1,
            statut_paiement='REUSSI'
        ).exists()

        return moyennes_valides and paiement_ok and not self.suspendu

    def mettre_a_jour_statut(self):
        """Met à jour automatiquement le statut académique"""
        if self.verifier_conditions_promotion():
            if self.classe.niveau_superieur:
                self.classe = self.classe.niveau_superieur
                self.redoublements = 0
                decision = 'ADMIS'
            else:
                decision = 'TERMINE'  # Si dernière classe
        else:
            self.redoublements += 1
            if self.redoublements >= 2:
                self.est_expulse = True
                decision = 'EXPULSE'
            else:
                decision = 'REDOUBLE'

        # Historique automatique
        HistoriqueAcademique.objects.create(
            eleve=self,
            periode=Periode.objects.active().first(),
            moyenne=BulletinPerformance.aggregate(Avg('moyenne_generale'))['moyenne_generale__avg'], # bulletins
            decision=decision,
            paiement_complet=self.paiements.filter(statut_paiement='REUSSI').exists()
        )

        self.save()

    def __str__(self):
        return str(self.prenom) + '-' + str(self.nom)

class HistoriqueAcademique(models.Model):
    DECISIONS = (
        ('ADMIS', 'Admis'),
        ('REDOUBLE', 'Redouble'),
        ('EXPULSE', 'Expulsé')
    )

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE)
    moyenne = models.FloatField()
    decision = models.CharField(max_length=10, choices=DECISIONS)
    paiement_complet = models.BooleanField()

    class Meta:
        unique_together = ('eleve', 'periode')

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
        if timezone.now().date() > self.date_fin:
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

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, related_name='administrateurs')
    role = models.CharField(max_length=20, choices=CHOICE_ROLE)

    telephone = PhoneNumberField(null=True, region='ML')
    email = models.EmailField(max_length=255)
    identifiant = models.CharField(max_length=20, unique=True, null=True)
    prenom = models.CharField(max_length=20)
    nom = models.CharField(max_length=20)
    username = models.CharField(max_length=20, unique=False, null=True, blank=True, verbose_name="Nom d'utilisateur", editable=False)
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
    REQUIRED_FIELDS = ['nom', 'prenom', 'telephone', 'username']

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
        unique_together = [
            ('tenant', 'identifiant'),
            ('tenant', 'telephone'),
            ('tenant', 'email')
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

    # def calculer_moyenne_generale(self):
    #     bulletin_matieres = self.classes.all()
    #
    #     moyennes_coefficient = defaultdict(float)
    #     for bm in bulletin_matieres:
    #         moyennes_coefficient[bm.matiere.id] += bm.note * bm.matiere.coefficient
    #
    #     print('moyenne_coeff', dict(moyennes_coefficient))
    #     matieres_classe = Matiere.objects.filter(classe=self.eleve.classe)
    #     self.moyenne_generale = calculer_moyenne_generale(moyennes_coefficient, matieres_classe)

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
        # self.calculer_moyenne_generale()

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




class TranchePaiement(models.Model):
    STATUT_CHOICES = [
        ('NON_ECHEU', 'Non échue'),
        ('ECHEU', 'Échue'),
        ('PAYE', 'Payée'),
        ('PARTIEL', 'Partiellement payé'),
    ]

    periode = models.ForeignKey('PeriodePaiement', on_delete=models.CASCADE)
    date_echeance = models.DateField()
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    ordre = models.PositiveIntegerField()
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='NON_ECHEU')


    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"Tranche {self.ordre} - {self.montant}€"

class PeriodePaiement(models.Model):
    MODE_PAIEMENT_CHOICES = [
        ('FULL', 'Paiement unique'),
        ('PARTIEL', 'Paiement échelonné'),
    ]

    nom = models.CharField(max_length=50)
    date_debut = models.DateField()
    date_fin = models.DateField()
    montant_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(5000)]
    )
    classe = models.ManyToManyField('Classe')
    examen = models.ForeignKey('Examen', on_delete=models.CASCADE)
    mode_paiement = models.CharField(
        max_length=7,
        choices=MODE_PAIEMENT_CHOICES,
        default='FULL'
    )
    nombre_tranches = models.PositiveIntegerField(
        default=1,
        help_text="Nombre de tranches pour le paiement échelonné"
    )
    rappel_jours = models.PositiveIntegerField(default=3)

    modalites_paiement = models.TextField(
        blank=True,
        help_text="Modalités de paiement spécifiques"
    )

    historique_modifications = models.JSONField(
        blank=True,
        null=True,
        help_text="Historique des modifications de la période"
    )


    def __str__(self):
        return f"{self.nom} ({self.date_debut} - {self.date_fin})"

    def generer_tranches(self):
        """Génère automatiquement les tranches 50%/25%/25% avec des dates échelonnées"""
        from django.db import transaction
        with transaction.atomic():  # Transaction atomique pour éviter les incohérences
            # Suppression des anciennes tranches existantes
            self.tranchepaiement_set.all().delete()

            if self.mode_paiement != 'PARTIEL' or self.nombre_tranches != 3:
                raise ValidationError("Cette méthode nécessite le mode PARTIEL avec exactement 3 tranches")

            total = self.montant_total
            delta_days = (self.date_fin - self.date_debut).days

            # Calcul des montants avec arrondi décimal
            amounts = [
                total * Decimal('0.50'),  # 50%
                total * Decimal('0.25'),  # 25%
                total * Decimal('0.25')  # 25%
            ]
            print(amounts)

            # Vérification que la somme est correcte
            if sum(amounts) != total:
                # Ajustement de la dernière tranche pour compenser les erreurs d'arrondi
                amounts[-1] = total - sum(amounts[:2])

            # Calcul des dates échelonnées
            dates = [
                self.date_debut + timedelta(days=delta_days // 3),
                self.date_debut + timedelta(days=2 * delta_days // 3),
                self.date_fin
            ]

            # Création des tranches
            for i, (amount, date) in enumerate(zip(amounts, dates), start=1):
                TranchePaiement.objects.create(
                    periode=self,
                    ordre=i,
                    montant=amount.quantize(Decimal('0.01')),  # Arrondi à 2 décimales
                    date_echeance=date,
                    statut='NON_ECHEU'
                )

            # Validation de la cohérence des données
            self.full_clean()

    def montant_restant_eleve(self, eleve):
        if self.mode_paiement == 'FULL':
            return self.montant_total - self.montant_paye_eleve(eleve)
        else:
            return sum(
                tranche.montant_restant(eleve)
                for tranche in self.tranchepaiement_set.all()
            )

    def montant_paye_eleve(self, eleve):
        return self.paiement_set.filter(
            eleve=eleve,
            statut_paiement='REUSSI'
        ).aggregate(total=models.Sum('montant_paye'))['total'] or 0

    def prochaine_tranche_eleve(self, eleve):
        return self.tranchepaiement_set.exclude(
            paiement__eleve=eleve,
            paiement__statut_paiement='REUSSI'
        ).order_by('date_echeance').first()

    def generer_echeancier_pdf(self, eleve):
        # Génération d'un PDF personnalisé avec les échéances
        pass

    def envoyer_rappel_automatique(self):
        # Intégration avec un système d'envoi d'emails/SMS
        pass


class Paiement(models.Model):
    MODE_CHOICES = [
        ('ORANGE', 'Orange Money'),
        ('MALITEL', 'M-Money'),
        ('ESPECES', 'Espèces')
    ]

    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('PARTIEL', 'Paiement partiel'),
        ('REUSSI', 'Paiement réussi'),
        ('ECHOUE', 'Paiement échoué'),
        ('ANNULE', 'Paiement annulé'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='paiements')
    periode = models.ForeignKey(PeriodePaiement, on_delete=models.CASCADE)
    tranche = models.ForeignKey(
        TranchePaiement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Tranche concernée (si paiement échelonné)"
    )
    montant_paye = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(500)]
    )
    date_paiement = models.DateTimeField(auto_now_add=True)
    mode_paiement = models.CharField(max_length=10, choices=MODE_CHOICES)
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Référence transaction"
    )
    statut_paiement = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='EN_ATTENTE'
    )
    caissier = models.ForeignKey(
        Administrateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_encaisses'
    )
    numero_quittance = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )
    preuve_paiement = models.FileField(
        upload_to='preuves_paiement/',
        null=True,
        blank=True,
        help_text="Scan du reçu pour paiement mobile"
    )
    commentaire = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_paiement']
        permissions = [
            ('confirmer_paiement', 'Peut confirmer les paiements'),
            ('annuler_paiement', 'Peut annuler les paiements')
        ]

    def __str__(self):
        return f"Paiement #{self.numero_quittance} - {self.eleve}"

    @property
    def solde_restant(self):
        if self.tranche:
            total_tranche = self.tranche.montant
            paye_tranche = Paiement.objects.filter(
                tranche=self.tranche,
                statut_paiement__in=['REUSSI', 'PARTIEL']
            ).aggregate(total=Sum('montant_paye'))['total'] or Decimal('0.00')
            return max(total_tranche - paye_tranche, Decimal('0.00'))

        total_periode = self.periode.montant_total
        paye_periode = Paiement.objects.filter(
            periode=self.periode,
            eleve=self.eleve,
            statut_paiement__in=['REUSSI', 'PARTIEL']
        ).aggregate(total=Sum('montant_paye'))['total'] or Decimal('0.00')
        return max(total_periode - paye_periode, Decimal('0.00'))

    def est_complet(self):
        return self.solde_restant <= Decimal('0.00')

    def mettre_a_jour_statut(self):
        if self.statut_paiement in ['ANNULE', 'ECHOUE']:
            return

        if self.est_complet():
            self.statut_paiement = 'REUSSI'
        elif self.montant_paye > Decimal('0.00'):
            self.statut_paiement = 'PARTIEL'
        else:
            self.statut_paiement = 'EN_ATTENTE'

        self.save()
        self._mettre_a_jour_tranche()

    def _mettre_a_jour_tranche(self):
        if self.tranche:
            total_paye = self.tranche.paiement_set.filter(
                statut_paiement__in=['REUSSI', 'PARTIEL']
            ).aggregate(total=Sum('montant_paye'))['total'] or Decimal('0.00')

            if total_paye >= self.tranche.montant:
                self.tranche.statut = 'PAYE'
            elif total_paye > 0:
                self.tranche.statut = 'PARTIEL'
            else:
                self.tranche.statut = 'ECHEU' if self.tranche.date_echeance < timezone.now().date() else 'NON_ECHEU'

            self.tranche.save()

    def save(self, *args, **kwargs):
        if not self.numero_quittance:
            prefix = 'Q' + timezone.now().strftime('%y%m%d')
            last_q = Paiement.objects.filter(numero_quittance__startswith=prefix).count()
            self.numero_quittance = f"{prefix}-{last_q + 1:04d}"

        if self.mode_paiement == 'ESPECES' and not self.transaction_id:
            self.transaction_id = f"ESP-{self.numero_quittance}"

        if self.mode_paiement in ['ORANGE', 'MALITEL'] and not self.transaction_id:
            raise ValidationError("Les paiements mobiles nécessitent une référence de transaction")

        super().save(*args, **kwargs)
        self.mettre_a_jour_statut()


class AccessLog(models.Model):
    user = models.ForeignKey('Administrateur', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    # Champs supplémentaires pour stocker les informations utilisateur indépendamment du modèle d'utilisateur
    custom_user_id = models.PositiveIntegerField(null=True, blank=True)
    custom_user_type = models.CharField(max_length=50, null=True, blank=True)  # Pour stocker le nom du modèle d'utilisateur
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100)
    url = models.CharField(max_length=500)
    details = models.JSONField(default=dict)
    status = models.CharField(max_length=20)

    @classmethod
    def log(cls, request, action, details=None, status='success'):
        if request.user.is_authenticated:
            # Obtenir le type et l'ID de l'utilisateur indépendamment du modèle réel
            user_type = request.user.__class__.__name__
            user_id = request.user.id

            # Créer une entrée de journal avec le type et l'ID de l'utilisateur
            cls.objects.create(
                user=None,  # Ne pas utiliser la ForeignKey directement
                custom_user_id=user_id,
                custom_user_type=user_type,
                action=action,
                url=request.get_full_path(),
                details=details or {},
                status=status
            )
        else:
            cls.objects.create(
                user=None,
                custom_user_id=None,
                custom_user_type=None,
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

    requester = models.ForeignKey('Administrateur',
                                  related_name='requests_created',
                                  on_delete=models.CASCADE)
    approver = models.ForeignKey('Administrateur',
                                 related_name='requests_to_approve',
                                 null=True,
                                 on_delete=models.SET_NULL)
    action_type = models.CharField(max_length=50)
    target_object = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)
    comments = models.TextField(blank=True)
    action_metadata = models.JSONField(null=True)

    def approve(self, approver):
        # Vérifier que l'approbateur est un directeur
        if not approver.role == 'DIRECTEUR':
            raise PermissionError("Seul le directeur peut approuver les demandes")

        self.status = 'APPROVED'
        self.approver = approver
        self.resolved_at = timezone.now()
        self.save()
        self.execute_action()

        # Enregistrer l'action dans les logs
        AccessLog.objects.create(
            user=None,
            custom_user_id=approver.id,
            custom_user_type=approver.__class__.__name__,
            action=f"APPROVAL_{self.action_type}",
            url="",
            details={"request_id": self.id, "target": self.target_object},
            status="success"
        )

    def reject(self, approver, reason):
        # Vérifier que l'approbateur est un directeur
        if not approver.role == 'DIRECTEUR':
            raise PermissionError("Seul le directeur peut rejeter les demandes")

        self.status = 'REJECTED'
        self.approver = approver
        self.comments = reason
        self.resolved_at = timezone.now()
        self.save()

        # Enregistrer l'action dans les logs
        AccessLog.objects.create(
            user=None,
            custom_user_id=approver.id,
            custom_user_type=approver.__class__.__name__,
            action=f"REJECTION_{self.action_type}",
            url="",
            details={"request_id": self.id, "target": self.target_object, "reason": reason},
            status="success"
        )

    def execute_action(self):
        """
        Exécute l'action approuvée en fonction du type d'action.
        Cette méthode est appelée automatiquement lorsqu'une demande est approuvée.
        """
        from django.urls import resolve, Resolver404
        from django.http import HttpRequest
        from django.contrib.auth.models import AnonymousUser

        # Récupérer les informations de la demande
        action_type = self.action_type
        target_object = self.target_object
        metadata = self.action_metadata

        try:
            # Créer une requête simulée pour exécuter la vue
            request = HttpRequest()
            request.method = 'POST'
            request.user = self.requester
            request.META = {'HTTP_HOST': 'localhost:8000'}

            # Ajouter les données POST
            if 'post_data' in target_object:
                from django.http import QueryDict
                post_data = QueryDict('', mutable=True)
                for key, value in target_object['post_data'].items():
                    if isinstance(value, list):
                        post_data.setlist(key, value)
                    else:
                        post_data[key] = value
                request.POST = post_data

            # Essayer de résoudre l'URL pour obtenir la vue
            if 'url' in target_object:
                try:
                    resolver_match = resolve(target_object['url'])
                    view_func = resolver_match.func
                    args = metadata.get('args', [])
                    kwargs = metadata.get('kwargs', {})

                    # Ajouter un indicateur pour éviter les boucles infinies
                    request.is_approved_action = True

                    # Exécuter la vue
                    response = view_func(request, *args, **kwargs)

                    # Enregistrer le succès dans les logs
                    AccessLog.objects.create(
                        user=None,
                        custom_user_id=self.approver.id if self.approver else None,
                        custom_user_type=self.approver.__class__.__name__ if self.approver else None,
                        action=f"EXECUTED_{action_type}",
                        url=target_object.get('url', ''),
                        details={
                            "request_id": self.id,
                            "target": target_object,
                            "result": "success"
                        },
                        status="success"
                    )

                    return True
                except Resolver404:
                    # Enregistrer l'échec dans les logs
                    AccessLog.objects.create(
                        user=None,
                        custom_user_id=self.approver.id if self.approver else None,
                        custom_user_type=self.approver.__class__.__name__ if self.approver else None,
                        action=f"EXECUTION_FAILED_{action_type}",
                        url=target_object.get('url', ''),
                        details={
                            "request_id": self.id,
                            "target": target_object,
                            "error": "URL not found"
                        },
                        status="error"
                    )
                    return False

            # Si nous ne pouvons pas exécuter l'action automatiquement,
            # nous enregistrons simplement que l'action a été approuvée
            AccessLog.objects.create(
                user=None,
                custom_user_id=self.approver.id if self.approver else None,
                custom_user_type=self.approver.__class__.__name__ if self.approver else None,
                action=f"APPROVED_{action_type}",
                url="",
                details={
                    "request_id": self.id,
                    "target": target_object,
                    "note": "Action approved but not automatically executed"
                },
                status="success"
            )
            return True

        except Exception as e:
            # En cas d'erreur, enregistrer l'échec dans les logs
            AccessLog.objects.create(
                user=None,
                custom_user_id=self.approver.id if self.approver else None,
                custom_user_type=self.approver.__class__.__name__ if self.approver else None,
                action=f"EXECUTION_ERROR_{action_type}",
                url=target_object.get('url', ''),
                details={
                    "request_id": self.id,
                    "target": target_object,
                    "error": str(e)
                },
                status="error"
            )
            return False

    @classmethod
    def create_request(cls, requester, action_type, target_object, action_metadata):
        """
        Crée une nouvelle demande d'approbation.

        Args:
            requester: L'utilisateur qui fait la demande
            action_type: Le type d'action demandée
            target_object: L'objet cible de l'action (en format JSON)
            action_metadata: Métadonnées supplémentaires pour l'action

        Returns:
            La demande d'approbation créée
        """
        request = cls.objects.create(
            requester=requester,
            action_type=action_type,
            target_object=target_object,
            action_metadata=action_metadata,
            status='PENDING'
        )

        # Enregistrer l'action dans les logs
        AccessLog.objects.create(
            user=None,
            custom_user_id=requester.id if requester else None,
            custom_user_type=requester.__class__.__name__ if requester else None,
            action=f"REQUEST_{action_type}",
            url="",
            details={"request_id": request.id, "target": target_object},
            status="success"
        )

        return request
