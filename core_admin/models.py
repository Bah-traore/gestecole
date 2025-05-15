from django.contrib.auth.models import AbstractUser, Permission, Group
from django.db import models

class SuperAdmin(AbstractUser):
    is_superadmin = models.BooleanField(default=True)
    
    groups = models.ManyToManyField(
        Group,
        verbose_name='Groupes',
        blank=True,
        related_name='superadmin_groups',  # ← Unique
        help_text='Groupes associés au superadmin',
    )
    
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='Permissions',
        blank=True,
        related_name='superadmin_user_permissions',  # ← Unique
        help_text='Permissions spécifiques au superadmin',
    )
    # Ajoute d'autres champs si besoin
# (Vide ou inutile, car on utilise le modèle Tenant déjà existant dans APP_G2S)


