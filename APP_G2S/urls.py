from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,  include
from . import views
# from .views import profile_view, logout_view, profile_agent_view
from rest_framework import routers

from .services.generate_BULLETIN.generate_bulletins import generate_bulletins
from .services.request_perso.requests import get_eleves_par_classe, get_eleves_classe
from .views import api_matieres

# from APP_G2S.API.viewset import SecureAuthViewSet, ContraventionViewSet


# router = routers.DefaultRouter()
# router.register(r'auth', SecureAuthViewSet, basename='auth')
# # router.register(r'citoyens', CitoyenViewset)
# # router.register(r'agents', AgentViewset)
# router.register(r'contraventions', ContraventionViewSet, basename='contraventions')

urlpatterns = [
    path('', views.Admininstrateur, name='connexion_admin'),
    # path('api/', include(router.urls)),
    path('index/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard_eleve/', views.dashboard_eleve, name='dashboard_eleve'),
    path('liste_eleves/', views.liste_eleves, name='eleve_gestion'),
    path('eleve/<int:eleve_id>/', views.detail_eleve, name='detail_eleve'),
    path('enseignant/<int:enseignant_id>/', views.detail_enseignant, name='detail_enseignant'),
    path('emploi_du_temps/', views.emploi_du_temps, name='emploi_du_temps'),
    path('emploi_du_temps/ajouter', views.ajouter_emploi, name='ajouter_emploi'),
    path('bulletins/', views.liste_bulletins, name='bulletins'),
    path('ajouter-bulletin/', views.ajouter_bulletin, name='ajouter_bulletin'),
    path('bulletin/<int:bulletin_id>/', views.detail_bulletin, name='detail_bulletin'),
    # path('administateur/enseignants/ajouter/', views.ajouter_enseignant, name='ajouter_enseignant'),
    path('administrateur/enseignants/ajouter/', views.ajouter_enseignant, name='ajouter_enseignant'),
    path('ajouter-eleve/', views.ajouter_eleve, name='ajouter_eleve'),

    path('administateur/enseignants/', views.enseignant_gestion, name='enseignant_gestion'),
    path('enseignant/<int:enseignant_id>/supprimer/', views.supprimer_enseignant,
    name='supprimer_enseignant'),
    path('enseignant/<int:enseignant_id>/modifier/', views.modifier_enseignant,
    name='modifier_enseignant'),
    path('ajouter-classe/', views.ajouter_classe, name='ajouter_classe'),
    path('classes/', views.liste_classes, name='liste_classes'),
    path('modifier_classe/<int:classe_id>/', views.modifier_classe, name='modifier_classe'),
    path('ajouter-matiere/', views.ajouter_matiere, name='ajouter_matiere'),
    path('matiere/', views.liste_matieres, name='liste_matieres'),
    path('api/matiere/', api_matieres, name='api_matieres'),
    path('examens/', views.liste_examens, name='liste_examens'),
    path('creer-examen/', views.creer_examen, name='creer_examen'),
    path('examen/<int:examen_id>/', views.detail_examen, name='detail_examen'),
    path('get-matiere/', views.get_matieres_par_classe, name='get_matieres'),
    path('saisir-notes/', views.saisir_notes, name='saisir_notes'),
    path('get_eleves_classe/', get_eleves_classe, name='get_eleves_classe'),
    path('get_eleves_par_classe/', get_eleves_par_classe, name='get_eleves_par_classe'),
    # path('get_eleves_saisir_notes/', get_eleves_saisir_notes, name='get_eleves_saisir_notes'),

                  path('api/eleves/', views.api_eleves, name='api_eleves'),
                  path('api/examens/<int:examen_id>/', views.api_examens, name='api_examens'),


    path('absences/', views.liste_absences, name='liste_absences'),
    path('ajouter-absence/', views.ajouter_absence, name='ajouter_absence'),
    path('supprimer-absence/<int:absence_id>/', views.supprimer_absence, name='supprimer_absence'),
    path('absences/modifier/<int:absence_id>/', views.modifier_absence, name='modifier_absence'),
    path('absences/pdf/', views.generer_pdf_absences, name='pdf_absences'),
    path('absences/excel/', views.exporter_excel_absences, name='excel_absences'),



    path('generate_bulletins/', generate_bulletins, name='generate_bulletins'),
    # path('generate_bulletins/', views.generate_bulletins, name='generate_bulletins'),
    path('gestion-periodes/', views.reglement_periode, name='gestion_periodes'),
    path('logout/admin/', views.logout_view, name='logout_admin'),

    path('paiement/especes/', views.enregistrer_paiement_especes,name='enregistrer_paiement_especes'),
    path('paiement/annuler/<int:paiement_id>/', views.annuler_paiement, name='annuler_paiement'),
    path('paiement/recherche_eleves/', views.recherche_eleves, name='recherche_eleves'),
    path('paiement/exporter_paiements_excel/', views.exporter_paiements_excel, name='exporter_paiements_excel'),

    path('paiements/', views.dashboard_paiements, name='gestion_paiements'),
    path('api/paiement/callback/', views.callback_paiement, name='callback_paiement'),
    path('get_emplois/', views.get_emplois, name='get_emplois'),
    path('historique-paiements/<int:eleve_id>/', views.historique_paiements, name='historique_paiements'),


    path('paiement/choix/<int:eleve_id>/', views.choix_mode_paiement, name='choix_paiement'),
    path('api/initier-paiement/', views.initier_paiement_mobile, name='initier_paiement'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)