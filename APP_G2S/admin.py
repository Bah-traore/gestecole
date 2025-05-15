import json

from django.contrib import admin
from django.utils.html import format_html
# from docutils.transforms.peps import non_masked_addresses

from APP_G2S.models import *

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect

HIERARCHY = {
    'DIRECTEUR': ['view_all', 'approve_all'],
    'CENSEUR': ['manage_pedagogy', 'validate_absences'],
    'COMPTABLE': ['financial_operations', 'generate_reports'],
    'SURVEILLANT': ['track_absences', 'manage_discipline']
}

def create_groups(sender, **kwargs):
    for role, perms in HIERARCHY.items():
        group, created = Group.objects.get_or_create(name=role)
        for perm in perms:
            # Trouver la permission via son codename et content_type
            app_label, codename = perm.split('.')
            content_type = ContentType.objects.get(app_label=app_label)
            permission = Permission.objects.get(
                codename=codename,
                content_type=content_type
            )
            group.permissions.add(permission)

@admin.register(Administrateur)
class AdministrationAdmin(admin.ModelAdmin):
    list_display = ['prenom', 'nom', 'telephone']
    fieldsets = (
        ('Information', {'fields': ('prenom', 'nom', 'identifiant', 'email', 'telephone', 'password')}),
        ('Rôle', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_admin', 'groups', 'user_permissions')}),
    )


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'status')
    # list_filter = ('status')
    search_fields = ('user__username', 'action')
    readonly_fields = ('details_prettified',)

    def details_prettified(self, obj):
        return format_html("<pre>{}</pre>", json.dumps(obj.details, indent=2))

@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'age', 'residence']

@admin.register(BulletinPerformance)
class BulletinPerformanceAdmin(admin.ModelAdmin):
    list_display = (['eleve', 'date_creation', 'moyenne_generale', 'appreciation', 'classement'])

@admin.register(BulletinMatiere)
class BulletinMatiereAdmin(admin.ModelAdmin):
    list_display = (['bulletin', 'matiere', 'note'])

@admin.register(Periode)
class PeriodeAdmin(admin.ModelAdmin):
    list_display = ['numero','date_debut', 'date_fin', 'annee_scolaire', 'cloture']
    actions = ['cloturer_periode']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('promotion-auto/', self.admin_site.admin_view(self.promotion_auto))
        ]
        return custom_urls + urls

    def promotion_auto(self, request):
        from django.core.management import call_command
        call_command('promotion_auto')
        return redirect('..')

    def cloturer_periode(self, request, queryset):
        queryset.update(cloture=True)

@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ['niveau', 'responsable']

@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = ['nom_complet']

@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ['nom', 'coefficient']


@admin.register(EmploiDuTemps)
class EmploiDuTempsAdmin(admin.ModelAdmin):
    list_display = ('matiere', 'classe', 'date', 'start_time', 'salle', 'conflit_alert')
    list_filter = ('classe', 'enseignant', 'date')
    search_fields = ('matiere__nom', 'salle')

    def conflit_alert(self, obj):
        conflits = EmploiDuTemps.objects.filter(
            models.Q(enseignant=obj.enseignant) | models.Q(classe=obj.classe),
            date=obj.date,
            start_time__lt=obj.end_time,
            end_time__gt=obj.start_time
        ).exclude(pk=obj.pk)
        return "⚠ CONFLIT" if conflits.exists() else "✅ OK"

    conflit_alert.short_description = "État"

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'valeur', 'date']

@admin.register(NoteExamen)
class NoteExamenAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'matiere', 'note']

@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ['nom', 'date']
@admin.register(PeriodePaiement)
class PeriodePaiementAdmin(admin.ModelAdmin):
    list_display = ['examen', 'nom', 'date_debut', 'date_fin', 'montant_total', 'rappel_jours', 'modalites_paiement', 'mode_paiement', 'nombre_tranches']
