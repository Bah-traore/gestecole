from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from . import views
# from .views import profile_view, logout_view, profile_agent_view
from rest_framework import routers

from .services.generate_BULLETIN.generate_bulletins import generate_bulletins
from .services.generatrice_pdf_excel_imprimer.pdf_generateur import generer_pdf_absences, generer_pdf_eleves, \
    generer_pdf_matieres, generer_pdf_bulletins
from .services.request_perso.requests import get_eleves_par_classe, get_eleves_classe, get_eleves
from .views import api_matieres, ValiderPaiementView, CaisseDashboardView, EncaissementView, AnnulationPaiementView, \
    DashboardPaiementsView, ChoixModePaiementView, InitierPaiementMobileView, HistoriquePaiementsView, \
    CreerPeriodePaiementView, GestionPaiementsView, ajouter_historique_academique, liste_historique_academique

# from APP_G2S.API.viewset import SecureAuthViewSet, ContraventionViewSet


# router = routers.DefaultRouter()
# router.register(r'auth', SecureAuthViewSet, basename='auth')
# # router.register(r'citoyens', CitoyenViewset)
# # router.register(r'agents', AgentViewset)
# router.register(r'contraventions', ContraventionViewSet, basename='contraventions')
urlpatterns = [
    path('', views.dashboard_admin, name='home'),  # ou une autre vue d'accueil
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
    path('modifier_examen/<int:examen_id>/', views.modifier_examen, name='modifier_examen'),
    path('examen/<int:examen_id>/', views.detail_examen, name='detail_examen'),
    path('get-matiere/', views.get_matieres_par_classe, name='get_matieres'),
    path('saisir-notes/', views.saisir_notes, name='saisir_notes'),
    path('get_eleves_classe/', get_eleves_classe, name='get_eleves_classe'),
    path('get_eleves_par_classe/', get_eleves_par_classe, name='get_eleves_par_classe'),
    path('get_eleves/', get_eleves, name='get_eleves'),
    path('api/eleves/', views.api_eleves, name='api_eleves'),
    path('api/examens/<int:examen_id>/', views.api_examens, name='api_examens'),


    path('absences/', views.liste_absences, name='liste_absences'),
    path('ajouter-absence/', views.ajouter_absence, name='ajouter_absence'),
    path('supprimer-absence/<int:absence_id>/', views.supprimer_absence, name='supprimer_absence'),
    path('absences/modifier/<int:absence_id>/', views.modifier_absence, name='modifier_absence'),
    path('absences/pdf/', generer_pdf_absences, name='pdf_absences'),
    path('eleves/pdf/', generer_pdf_eleves, name='pdf_eleves'),
    path('matieres/pdf/', generer_pdf_matieres, name='pdf_matieres'),
    # path('enseignants/pdf/', generer_pdf_enseignants, name='pdf_enseignants'),
    path('bulletins/pdf/', generer_pdf_bulletins, name='pdf_bulletins'),
    path('absences/excel/', views.exporter_excel_absences, name='excel_absences'),

    path('generate_bulletins/', generate_bulletins, name='generate_bulletins'),

    path('gestion-periodes/', views.periode_scolaire, name='gestion_periodes'),
    path('gestion-periodes/modifier/<int:periode_id>/', views.modifier_periode, name='modifier_periode'),
    path('gestion-periodes/supprimer/<int:periode_id>/', views.supprimer_periode, name='supprimer_periode'),
    path('logout/admin/', views.logout_view, name='logout_admin'),

    # path('paiement/especes/<int:eleve_id>/', views.enregistrer_paiement_especes,name='enregistrer_paiement_especes'),
    # path('paiement/annuler/<int:paiement_id>/', views.annuler_paiement, name='annuler_paiement'),
    # path('paiement/recherche_eleves/', views.recherche_eleves, name='recherche_eleves'),
    path('paiement/exporter_paiements_excel/', views.exporter_paiements_excel, name='exporter_paiements_excel'),

    path('paiements/', DashboardPaiementsView.as_view(), name='dashboard_paiements'),
    path('paiements/gestion_paiements', GestionPaiementsView.as_view(), name='gestion_paiements'),

    path('api/paiement/callback/', views.callback_paiement, name='callback_paiement'),
    path('get_emplois/', views.get_emplois, name='get_emplois'),
    path('historique-paiements/<int:eleve_id>/', HistoriquePaiementsView.as_view(), name='historique_paiements'),


    path('paiement/choix/<int:eleve_id>/', ChoixModePaiementView.as_view(), name='choix_paiement'),
    path('api/initier-paiement/', InitierPaiementMobileView.as_view(), name='initier_paiement'),

    path('paiement/valider/<int:pk>/',ValiderPaiementView.as_view(), name='valider-paiement'),
    path('caisse/dashboard/',CaisseDashboardView.as_view(), name='caisse_dashboard'),
    path('paiement/encaissement/',EncaissementView.as_view(), name='encaissement'),
    path('paiement/annuler/<int:pk>/',AnnulationPaiementView.as_view(), name='annuler-paiement'),
    # path('api/load-tranches/',load_tranches, name='load_tranches'),




    path('api/tranche-info/', views.get_tranche_info, name='get_tranche_info'),

    path('creer_periode_de_paie/', CreerPeriodePaiementView.as_view(), name='creer_periode_paiement'),
    path('historique-academique/ajouter/', ajouter_historique_academique, name='ajouter_historique_academique'),
    path('historique-academique/', liste_historique_academique, name='liste_historique_academique'),
    path('statuts-academiques/', views.statuts_academiques, name='statuts_academiques'),

    # Erreur de type d'utilisateur
    path('erreur-user-type/', views.erreur_user_type, name='erreur_user_type'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
