import json
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.sessions.exceptions import SessionInterrupted
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction, models
from django.db.models import Sum, Avg, Count, Q, Prefetch
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth import login, logout
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from openpyxl.styles import Font, Alignment

from gestecole import settings
from gestecole.utils.calculatrice_bulletin import calculer_moyennes_coefficients, calculer_moyenne_generale
# from gestecole.utils.calculatrice_bulletin import calculer_moyennes
from gestecole.utils.decorateurs import citoyen_required, agent_required, administrateur_required
from gestecole.utils.file_handlers import save_files_to_temp
from gestecole.utils.idgenerateurs import SMSService, IDGenerator
from gestecole.utils.paiements import MalitelMoneyAPI, OrangeMoneyAPI
from gestecole.utils.services import EnseignantCreationService, MyLogin  # , LoginAdminFrom, get_client_ip
from .forms import LoginForm, LoginFormAgent, LoginAdminFrom, EleveCreationForm, BulletinForm, ExamenForm, \
    EnseignantCreationForm, MatiereForm, ClasseForm, PeriodeForm, AbsenceForm, PaiementFormEspeces, PeriodePaiementForm, \
    EmploiDuTempsForm
from django.conf import settings
from datetime import datetime


from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from .models import Note, Administrateur, Eleve, Matiere, Classe, EmploiDuTemps, Absence, Enseignant, \
    BulletinPerformance, BulletinMatiere, NoteExamen, Examen, PeriodePaiement, Periode, logger, Paiement

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from openpyxl import Workbook
from django.http import HttpResponse




ul = MyLogin()


@ratelimit(key='post:identifiant', rate='5/h', method='POST')
@csrf_protect
@ratelimit(key='ip', rate='10/m', block=True)
def Admininstrateur(request):
    if request.method == settings.METHODE_POST:
        form = LoginAdminFrom(data=request.POST)
        if form.is_valid():
            identifiant = form.cleaned_data['identifiant']
            password = form.cleaned_data['password']
            user = ul.login_user_Admin(identifiant, password)
            if user is not None:
                if user.is_admin and user.is_authenticated:
                    try:
                        login(request, user, backend='APP_G2S.auth_backends.AdminBackend')
                        return redirect('dashboard_admin')
                    except Exception as e:
                        messages.error(request, f"Erreur de connexion : {str(e)}")
                else:
                    messages.error(request, "Vous n'avez pas les droits de Super Agent.")
            else:
                messages.error(request, "Identifiant ou mot de passe incorrect.")
        else:
            messages.error(request, "Formulaire invalide.")
    else:
        form = LoginAdminFrom()
    return render(request, 'APP_G2S/connexion_admin.html', {'form': form})


# Login Citoyen
@ratelimit(key='post:telephone', rate='5/h', method='POST')
@csrf_protect
def login_view_eleve(request):
    if request.method == settings.METHODE_POST:
        form = LoginForm(data=request.POST)
        if form.is_valid():
            telephone = form.cleaned_data.get('telephone', None)
            password = form.cleaned_data.get('password', None)
            user = ul.login_user_Admin(telephone, password)
            if user is None:
                '''
                je vais gere la session ici par la cockie ou par le stokage de request au local
                '''
                messages.error(request, f'Telephone {telephone} inconnu')
                return redirect('login')
            login(request, user, backend='APP_G2S.auth_backends.TelephoneBackend')
        if request.user.is_authenticated:
            print(request.user.telephone)
            return redirect('dashboard_admin')
    else:
        form = LoginForm()
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)  # Session de 1h
    request.session['last_login'] = str(timezone.now())
    return render(request, 'APP_G2S/connexions/connexion.html', {'forms': form})


@ratelimit(key='post:matricule', rate='5/h', method='POST')
@csrf_protect
def login_view_agent(request):
    if request.method == settings.METHODE_POST:
        form = LoginFormAgent(request.POST)
        if form.is_valid():
            matricule = form.cleaned_data['matricule']
            password = form.cleaned_data['password']
            user = ul.login_user_Agent(matricule, password)

            if user is None:
                messages.error(request, "Matricule incorrect ou agent inactif.")
                return redirect('login_agent')
            if user.is_agent:
                login(request, user, backend='APP_G2S.auth_backends.MatriculeBackend')
                if request.user.is_authenticated:
                    return redirect('agent_dashboard')
            else:
                messages.error(request, "Mot de passe incorrect.")
        else:
            messages.error(request, "Données invalides.")
    else:
        form = LoginFormAgent()
    return render(request, 'APP_G2S/agent/login_agent.html', {'form': form})



@administrateur_required
# @permission_required('APP_G2S.view_all', raise_exception=True)
def dashboard_admin(request):
    if request.user.identifiant:
       if request.user.is_authenticated:
            admin = Administrateur.objects.get(identifiant=request.user.identifiant)
            return render(request, "APP_G2S/composant-admin/dashboard.html", {"user": admin})
       try:
           user_data = request.session['user_data']
       except SessionInterrupted:
           return HttpResponse("Session expired or invalid.", user_data)
       return redirect('connexion_admin')
    return HttpResponse("FORBIDDEN")




@administrateur_required
def dashboard_eleve(request):

    return render(request, "APP_G2S/composant-admin/dashboard_eleve.html")

# la gestion des eleves
@administrateur_required
def liste_eleves(request):
    eleves = Eleve.objects.all()
    matieres = Matiere.objects.all()
    classes_uniques = Classe.objects.distinct().order_by('id')
    return render(request, 'APP_G2S/composant-admin/liste_eleves.html', {"eleves": eleves, 'matiere': matieres, 'classes_uniques': classes_uniques})

@administrateur_required
def detail_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    notes = Note.objects.filter(eleve=eleve).select_related('matiere')
    note_examen = NoteExamen.objects.filter(eleve=eleve).select_related('matiere')
    absences = Absence.objects.filter(eleve=eleve).select_related('matiere')
    emploi = EmploiDuTemps.objects.filter(classe=eleve.classe).prefetch_related('matiere')

    context = {
        'eleve': eleve,
        'notes': notes,
        'notes_examen': note_examen,
        'emploi': emploi,
        'absences': absences,

    }
    return render(request, 'APP_G2S/composant-admin/detail_eleve.html', context)


# @administrateur_required
# def enseignant_gestion(request):
#
#     form = EnseignantCreationForm(data=request.POST)
#     if form.is_valid():
#         telephone = form.cleaned_data.get('telephone', 'N/A')
#         nom_complet = form.cleaned_data.get('nom_complet', 'N/A')
#         profile_picture = form.cleaned_data.get('profile_picture', 'N/A')
#         matiere = form.cleaned_data.get('matiere', 'N/A')
#
#     enseignant = Enseignant.objects.all()
#     context = {
#         'enseignant': enseignant,
#     }
#
#     return render(request, 'APP_G2S/composant-admin/liste_enseignant.html', context)
#


@administrateur_required
def detail_enseignant(request, enseignant_id):

    enseignant = get_object_or_404(Enseignant, id=enseignant_id)

    context = {
        'enseignant': enseignant,
    }

    return render(request, 'APP_G2S/composant-admin/detail_enseignant.html', context)


@administrateur_required
def emploi_du_temps(request):
    classe_selected = request.GET.get('classe')

    queryset = EmploiDuTemps.objects.all().select_related(
        'classe', 'matiere', 'enseignant'
    ).order_by('date', 'start_time')  # Utiliser les champs réels

    if classe_selected:
        queryset = queryset.filter(classe__id=classe_selected)

    context = {
        'emploi': queryset,
        'classes': Classe.objects.all(),
        'classe_selected': classe_selected
    }
    return render(request, 'APP_G2S/composant-admin/emploi_du_temps.html', context)


@administrateur_required
def liste_bulletins(request):
    bulletins = BulletinPerformance.objects.all().select_related('eleve').order_by('-date_creation')
    context = {
        'bulletins': bulletins,
    }
    return render(request, 'APP_G2S/composant-admin/liste_bulletins.html', context)


@administrateur_required
# @transaction.atomic
def ajouter_bulletin(request):
    # Initialisation des variables


    eleve = None
    classe = None
    periode_active = None
    form = BulletinForm(request.POST or None)
    context = {
        'form': form,
        'eleve': None,
        'eleves_classe': [],
        'notes_existantes': [],
        'notes_existantes_E': [],
        'matieres_classe': [],
        'moyennes_coefficient': {},
        'moyenne_generale': None,
        'classement': None,
        'periode_active': None,
        'bulletin_existant': None,
        'examens_valides': True
    }

    try:
        # Récupération de la période active
        periode_active = Periode.objects.prefetch_related('classe').get(is_active=True)
        context['periode_active'] = periode_active
    except Periode.DoesNotExist:
        messages.error(request, "Aucune période scolaire active configurée")
        return render(request, 'APP_G2S/composant-admin/ajouter_bulletin.html', context)

    # Gestion des paramètres GET/POST
    classe_id = request.GET.get('classe') or request.POST.get('classe')
    eleve_id = request.GET.get('eleve') or request.POST.get('eleve')

    if classe_id:
        try:
            classe = Classe.objects.prefetch_related('eleves', 'matieres').get(id=classe_id)
        except Classe.DoesNotExist:
            messages.error(request, "Classe introuvable")

        # Récupération de l'élève et mise à jour de la classe si nécessaire
    if eleve_id:
        try:
            eleve = Eleve.objects.select_related('classe').get(id=eleve_id)
            context['eleve'] = eleve

            # Définir la classe à partir de l'élève si non spécifiée
            if not classe and eleve.classe:
                classe = eleve.classe
                context['classe_selectionnee'] = classe

            # Vérification de la cohérence classe/élève
            if classe and eleve.classe != classe:
                messages.error(request, "L'élève ne fait pas partie de cette classe")
                return redirect('ajouter_bulletin')

            # Récupération des données pédagogiques
            matieres_classe = eleve.classe.matieres.all()
            context['matieres_classe'] = matieres_classe

            # Optimisation des requêtes de notes
            notes_existantes = Note.objects.filter(
                eleve=eleve,
                periode=periode_active
            ).select_related('matiere')

            notes_existantes_E = NoteExamen.objects.filter(
                eleve=eleve,
                periode=periode_active
            ).select_related('matiere')

            # Conversion en dictionnaire pour accès rapide
            notes_classe_dict = {n.matiere_id: n.valeur for n in notes_existantes}
            notes_exam_dict = {n.matiere_id: n.note for n in notes_existantes_E}

            # Calcul des moyennes
            moyennes_coefficient = calculer_moyennes_coefficients(
                notes_classe_dict,
                notes_exam_dict,
                matieres_classe
            )

            context.update({
                'notes_existantes': notes_existantes,
                'notes_existantes_E': notes_existantes_E,
                'moyennes_coefficient': moyennes_coefficient,
                'moyenne_generale': calculer_moyenne_generale(moyennes_coefficient, matieres_classe),
                'bulletin_existant': BulletinPerformance.objects.filter(
                    eleve=eleve,
                    periode=periode_active
                ).first()
            })

        except Eleve.DoesNotExist:
            messages.error(request, "Élève introuvable")

    # Gestion de la soumission du formulaire
    if request.method == 'POST':
        # Validation préalable
        if periode_active.cloture:
            messages.error(request, "Période clôturée - modifications impossibles")
            return redirect('ajouter_bulletin')

        # Vérification des examens associés
        examens_invalides = Examen.objects.filter(
            Q(periode=periode_active) &
            (Q(validite='FIN') | Q(date__lt=timezone.now().date()))
        ).exists()

        if examens_invalides:
            messages.error(request, "Examens invalides détectés")
            return redirect('ajouter_bulletin')

        if form.is_valid():
            try:
                # Création/mise à jour du bulletin
                bulletin, created = BulletinPerformance.objects.update_or_create(
                    eleve=eleve,
                    periode=periode_active,
                    defaults={
                        'appreciation': form.cleaned_data['appreciation'],
                        'moyenne_generale': context['moyenne_generale'],
                        'classes': eleve.classe,
                        'date_modification': timezone.now()
                    }
                )

                # Traitement des notes par matière
                bulletin_matiere_data = []
                for matiere in context['matieres_classe']:
                    note_classe = float(request.POST.get(f'note_classe_{matiere.id}', 0))
                    note_exam = float(request.POST.get(f'note_exam_{matiere.id}', 0))

                    # Calcul selon la pondération (classe: 1/3, examen: 2/3)
                    note_ponderee = (note_classe + (note_exam * 2)) / 3

                    bulletin_matiere_data.append(BulletinMatiere(
                        bulletin=bulletin,
                        matiere=matiere,
                        note=note_ponderee
                    ))

                # Mise à jour en masse
                BulletinMatiere.objects.bulk_create(
                    bulletin_matiere_data,
                    update_conflicts=True,
                    update_fields=['note'],
                    unique_fields=['bulletin', 'matiere']
                )

                messages.success(request,
                                 f"Bulletin {'mis à jour' if not created else 'créé'} avec succès"
                                 )

                # Redirection avec paramètres
                redirect_params = []
                if classe: redirect_params.append(f'classe={classe.id}')
                if eleve: redirect_params.append(f'eleve={eleve.id}')
                return redirect(f"{reverse('ajouter_bulletin')}?{'&'.join(redirect_params)}")

            except Exception as e:
                logger.error(f"Erreur d'enregistrement: {str(e)}", exc_info=True)
                messages.error(request, f"Erreur critique lors de l'enregistrement: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    # Préparation du contexte final
    context.update({
        'examens_valides': not Examen.objects.filter(
            periode=periode_active,
            validite='FIN'
        ).exists()
    })

    # Gestion des requêtes AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'moyenne_generale': context['moyenne_generale']
        })

    return render(request, 'APP_G2S/composant-admin/ajouter_bulletin.html', context)


from django.views.decorators.http import require_GET
from django.http import JsonResponse





def detail_bulletin(request, bulletin_id):
    bulletin = get_object_or_404(BulletinPerformance, id=bulletin_id)
    notes_details = bulletin.get_notes_details()

    class_stats = BulletinPerformance.objects.filter(
        eleve__classe=bulletin.eleve.classe,
        periode=bulletin.periode
    ).aggregate(
        avg_moyenne=Avg('moyenne_generale'),
        total=Count('id')
    )

    context = {
        'bulletin': bulletin,
        'notes_details': notes_details,
        'class_average': class_stats['avg_moyenne'] or 0,
        'class_total': class_stats['total'] or 0,
    }
    return render(request, 'APP_G2S/composant-admin/detail_bulletin.html', context)

@administrateur_required
def enseignant_gestion(request):
    enseignants = Enseignant.objects.all()
    context = {
        'enseignants': enseignants,
    }
    return render(request, 'APP_G2S/composant-admin/liste_enseignant.html', context)




@administrateur_required
def ajouter_enseignant(request):
    if request.method == settings.METHODE_POST:
        form = EnseignantCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                enseignant = form.save(commit=False)

                # Génération de l'ID enseignant
                enseignant.identifiant = IDGenerator.generate_teacher_id()
                password = IDGenerator.generatriceMDP_default()

                from django.contrib.auth.hashers import make_password
                enseignant.password = make_password(password)

                enseignant.is_enseignant = True

                enseignant.save()
                form.save_m2m()
                if SMSService.send_creation_sms(enseignant, password):
                    messages.success(request, "Enseignant créé avec succès ! SMS envoyé.")
                else:
                    messages.warning(request, "Enseignant créé mais échec d'envoi SMS")

                return redirect('enseignant_gestion')

            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {str(e)}")
                print(e)
        else:
            messages.error(request, "Formulaire invalide. Veuillez corriger les erreurs.")
    else:
        form = EnseignantCreationForm()

    enseignants = Enseignant.objects.all()
    return render(request, 'APP_G2S/composant-admin/ajouter_enseignant.html', {
        'enseignants': enseignants,
        'form': form
    })

@administrateur_required
def supprimer_enseignant(request, enseignant_id):
    enseignant = get_object_or_404(Enseignant, id=enseignant_id)
    if request.method == 'POST':
        enseignant.delete()
        messages.success(request, "Enseignant supprimé avec succès.")
        return redirect('enseignant_gestion')
    return render(request, 'APP_G2S/composant-admin/supprimer_enseignant.html', {'enseignant': enseignant})


@administrateur_required
def modifier_enseignant(request, enseignant_id):
    enseignant = get_object_or_404(Enseignant, id=enseignant_id)
    if request.method == 'POST':
        form = EnseignantCreationForm(request.POST, request.FILES, instance=enseignant)
        if form.is_valid():
            form.save()
            messages.success(request, "Enseignant modifié avec succès !")
            return redirect('enseignant_gestion')
    else:
        form = EnseignantCreationForm(instance=enseignant)
    return render(request, 'APP_G2S/composant-admin/modifier_enseignant.html', {'form': form})


@administrateur_required
def ajouter_eleve(request):
    if request.method == 'POST':
        form = EleveCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                eleve = form.save(commit=False)
                eleve.is_eleve = True

                password = IDGenerator.generatriceMDP_default()

                from django.contrib.auth.hashers import make_password
                eleve.password = make_password(password)
                user_id = f"{eleve.nom}-{eleve.prenom}"
                with transaction.atomic():
                    try:
                        temp_files = save_files_to_temp(request.FILES, user_id)
                        request.session['temp_files'] = temp_files
                    except Exception as e:
                        print(f"Erreur au niveau temp_files: {e}")
                        messages.error(request, f"Erreur au niveau temp_files: {e}")
                        return redirect('eleve_gestion')

                    if SMSService.send_creation_sms_eleve(eleve, password):
                        eleve.save()
                        form.save_m2m()
                        messages.success(request, "Élève créé avec succès. SMS envoyé!")
                        return redirect('eleve_gestion')
                    else:
                        messages.warning(request, "Élève créé mais échec d'envoi SMS")
                    return redirect('eleve_gestion')
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Erreur système : {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur sur le champ {field}: {error}")
            messages.error(request, "Formulaire invalide")
    else:
        form = EleveCreationForm()

    return render(request, 'APP_G2S/composant-admin/ajouter_eleve.html', {'form': form})


@administrateur_required
def ajouter_emploi(request):
    if request.method == 'POST':
        form = EmploiDuTempsForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                messages.success(request, "Cours ajouté avec succès !")
                return redirect('ajouter_emploi')
            else:
                # Afficher les erreurs dans la console
                print("Erreurs du formulaire:", form.errors)
                # Afficher les erreurs aux utilisateurs via messages
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            messages.error(request, f"ERREUR: {str(e)}")
            print(f"ERREUR: {str(e)}")
    else:
        form = EmploiDuTempsForm()

    emplois = EmploiDuTemps.objects.all().order_by('date', 'start_time')
    return render(request, 'APP_G2S/composant-admin/ajouter_emploi.html', {
        'form': form,
        'emplois': emplois
    })
@administrateur_required
def ajouter_note(request):

    return render(request, 'APP_G2S/composant-admin/ajouter_note.html')

@administrateur_required
# @staff_member_required
def liste_examens(request):
    # Validation et récupération des examens actifs
    examens = Examen.objects.all() # filter(validite='EN_COURS') \
        # .prefetch_related('matieres') \
        # .prefetch_related('classe') \
        # .order_by('-date')

    # Filtrage par classe valide
    classe_id = request.GET.get('classe')
    if classe_id and classe_id.isdigit():
        examens = examens.filter(classe__id=int(classe_id))

    context = {
        'examens': examens,
        'classes': Classe.objects.all() # filter(est_actif=True)
    }
    return render(request, 'APP_G2S/composant-admin/liste_examens.html', context)

@administrateur_required
def detail_examen(request, examen_id):
    examen = get_object_or_404(
        Examen.objects.all(), # select_related('classe').prefetch_related('matiere'),  # Correction ici
        pk=examen_id
    )

    print("examen", examen)

    # Récupérer les notes avec les élèves associés
    notes_examen = NoteExamen.objects.filter(examen=examen) \
        .select_related('eleve') \
        .order_by('eleve__nom')

    print("notes_examen", notes_examen)

    # Statistiques
    moyenne_generale = notes_examen.aggregate(
        avg_note=models.Avg('note')
    )['avg_note'] or 0

    context = {
        'examen': examen,
        'notes_examen': notes_examen,
        'moyenne_generale': round(moyenne_generale, 2),
        'note_max': notes_examen.aggregate(max=models.Max('note'))['max'] or 0,
        'note_min': notes_examen.aggregate(min=models.Min('note'))['min'] or 0,
    }
    return render(request, 'APP_G2S/composant-admin/detail_examen.html', context)


@csrf_protect
def saisir_notes(request):
    if request.method == 'POST':
        classe_id = request.POST.get('classe')
        matiere_id = request.POST.get('matiere')
        examen_id = request.POST.get('examen')

        try:
            classe = Classe.objects.get(id=classe_id)
            matiere = Matiere.objects.get(id=matiere_id)
            examen = Examen.objects.get(id=examen_id) if examen_id else None
            today = timezone.now().date()

            # Validation des contraintes
            periode = None
            periode_examen = None
            if examen:
                periode_examen = examen.periode
                if not (examen.date <= today <= examen.date_fin):
                    raise ValidationError("Hors période de l'examen")
            else:
                periode = Periode.objects.active().filter(
                    classe=classe,
                    date_debut__lte=today,
                    date_fin__gte=today
                ).first()
                periode_examen = Examen.objects.filter(validite="EN_COURS", periode=periode).first()
                print(periode_examen)
                if not periode:
                    raise ValidationError("Aucune période active")

            if periode.cloture or not periode.is_active:
                raise ValidationError("Période clôturée/inactive")

            # Traitement des notes
            for key, value in request.POST.items():
                # if key.startswith('classe'):
                #     classe = classe.objects.get(classe)
                if key.startswith('note_classe_'):
                    eleve_id = key.split('_')[2]
                    eleve = Eleve.objects.get(id=eleve_id)
                    Note.objects.update_or_create(
                        eleve=eleve,
                        matiere=matiere,
                        classe=classe,
                        periode=periode,
                        examen_reference_id=periode_examen.id,
                        defaults={'valeur': float(value), 'date': today}
                    )

                elif key.startswith('note_examen_'):
                    if type(value) == str:
                        continue
                    eleve_id = key.split('_')[2]
                    eleve = Eleve.objects.get(id=eleve_id)
                    NoteExamen.objects.update_or_create(
                        eleve=eleve,
                        matiere=matiere,
                        periode=periode,
                        examen=examen if examen else float(0),
                        defaults={'note': float(value), 'date': today}
                    )

            messages.success(request, "Notes sauvegardées")
            return redirect('saisir_notes')

        except Exception as e:
            messages.error(request, str(e))

    # GET: Afficher les données initiales
    classes = Classe.objects.all()
    matieres = Matiere.objects.all()
    examens_en_cours = Examen.objects.filter(validite='EN_COURS')
    examens_fin = Examen.objects.filter(validite='FIN')
    return render(request, 'APP_G2S/composant-admin/saisir_notes.html', {
        'classes': classes,
        'matieres': matieres,
        'examens_en_cours': examens_en_cours,
        'examens_fin': examens_fin
    })

@administrateur_required
def liste_notes(request):
    notes_classe = Note.objects.all().select_related('eleve', 'matiere')
    notes_examen = NoteExamen.objects.all().select_related('eleve', 'examen')

    return render(request, 'APP_G2S/composant-admin/liste_notes.html', {
        'notes_classe': notes_classe,
        'notes_examen': notes_examen
    })


from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def api_eleves(request):
    classe_id = request.GET.get('classe')
    matiere_id = request.GET.get('matiere')
    examen_id = request.GET.get('examen')

    eleves = Eleve.objects.filter(classe__id=classe_id)
    data = []
    today = timezone.now().date()

    periode = Periode.objects.active().filter(
        classe__id=classe_id,
        # date_debut__lte=today,
        # date_fin__gte=today,
        cloture=False
    ).first()
    print('periode', periode)

    for eleve in eleves:
        note_classe = float(0)
        note_examen = float(0)
        disabled = True



        try:
            if examen_id:
                examen = Examen.objects.get(id=examen_id)
                examen_valide = (
                    examen.validite == 'EN_COURS' and
                    examen.date <= today <= examen.date_fin and
                    examen.periode.is_active and
                    not examen.periode.cloture and
                    examen.matieres.filter(id=matiere_id).exists()
                )

                if examen_valide:
                    disabled = False
                    note = NoteExamen.objects.filter(
                        eleve=eleve,
                        examen=examen,
                        matiere_id=matiere_id
                    ).first()
                    note_examen = note.note if note else float(0)

                    n_classe = Note.objects.filter(
                        eleve=eleve,
                        matiere__id=matiere_id,
                        periode=periode
                    ).first()
                    note_classe = n_classe.valeur if n_classe else float(0)

            else:

                if periode:
                    disabled = False
                    n_classe = Note.objects.filter(
                        eleve=eleve,
                        matiere__id=matiere_id,
                        periode=periode
                    ).first()
                    note_classe = n_classe.valeur if n_classe else float(0)


                    # # Note d'examen liée à la période
                    # n_examen = NoteExamen.objects.filter(
                    #     eleve=eleve,
                    #     matiere_id=matiere_id,
                    #     periode=periode
                    # ).first()
                    # note_examen = n_examen.note if n_examen else ''
                    # print('n_examen', n_examen)

        except Examen.DoesNotExist:
            messages.error(request, "Examen n'existe pas ou non enregistré")
        except Exception as e:
            print('dans api_eleves', str(e))
            messages.error(request, 'dans api_eleves', str(e))

        data.append({
            'id': eleve.id,
            'nom_complet': f"{eleve.prenom} {eleve.nom}",
            'note_classe': float(note_classe),
            'note_examen': float(note_examen),
            'disabled': disabled
        })

        # print('la data c\'est dire les donnees', data)

    return JsonResponse(data, safe=False)


@require_GET
def api_examens(request, examen_id):
    try:
        examen = Examen.objects.get(id=examen_id)
        print('examen.periode.cloture', examen.periode.cloture)
        return JsonResponse({
            'date': examen.date.strftime("%d-%m-%y"),
            'date_fin': examen.date_fin.strftime("%d-%m-%y"),
            'periode_active': examen.periode.is_active,
            'periode_cloture': examen.periode.cloture,
            'validite': examen.validite
        })
    except Examen.DoesNotExist:
        return JsonResponse({'error': 'Examen non trouvé'}, status=404)


@administrateur_required
def creer_examen(request):
    if request.method == 'POST':
        form = ExamenForm(request.POST)
        if form.is_valid():
            try:
                # Validation 1 : Vérifier les matières via form.cleaned_data
                # if not form.cleaned_data.get('matiere'):
                #     form.add_error('matiere', "Sélectionnez au moins une matière")
                #     raise ValidationError("Matière manquante")

                # Validation 2 : Date cohérente
                if form.cleaned_data['validite'] == 'FIN' and form.cleaned_data['date'] > timezone.now().date():
                    form.add_error('validite', "Un examen terminé ne peut pas avoir une date future")
                    raise ValidationError("Date incohérente")

                # Sauvegarde de l'objet principal
                examen = form.save()  # Sauvegarde directe (pas besoin de commit=False)

                # # Sauvegarde des relations ManyToMany
                # form.save_m2m()  # Optionnel ici car form.save() le fait déjà

                messages.success(request, "Examen créé avec succès !")
                return redirect('liste_examens')

            except ValidationError as e:
                messages.error(request, str(e))
        else:
            # Afficher les erreurs du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ExamenForm()

    return render(request, 'APP_G2S/composant-admin/creer_examen.html', {'form': form})


@administrateur_required
def reglement_periode(request):
    try:
        # Récupération de la période active existante
        active_period = Periode.objects.filter(is_active=True).first()
    except AttributeError:
        messages.error(request, "Erreur de configuration : Manager 'active' non défini")
        active_period = None

    # Initialisation du formulaire
    form = PeriodeForm(instance=active_period)
    periodes_actives = Periode.objects.all()

    if request.method == "POST":
        try:
            form = PeriodeForm(request.POST, instance=active_period)

            if form.is_valid():
                # Sauvegarde en deux étapes pour les relations M2M
                periode = form.save(commit=False)
                periode.save()  # Crée l'ID avant de gérer les relations
                form.save_m2m()  # Sauvegarde les relations ManyToMany

                messages.success(request, "Période enregistrée avec succès")
                return redirect('gestion_periodes')
            else:
                messages.error(request, "Formulaire invalide. Veuillez corriger les erreurs.")

        except Exception as e:
            logger.error(f"Erreur critique : {str(e)}", exc_info=True)
            messages.error(request, f"Erreur lors de l'enregistrement : {str(e)}")

    return render(request, 'APP_G2S/composant-admin/reglements_periode.html', {
        'form': form,
        'periodes_actives': periodes_actives
    })


@administrateur_required
def ajouter_classe(request):
    if request.method == 'POST':
        form = ClasseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Classe ajoutée avec succès !")
            return redirect('liste_classes')
    else:
        form = ClasseForm()

    context = {
        'form': form,
        'enseignants': Enseignant.objects.all()
    }
    return render(request, 'APP_G2S/composant-admin/ajouter_classe.html', context)


@administrateur_required
def modifier_classe(request, classe_id):
    classe = get_object_or_404(Classe, id=classe_id)
    if request.method == 'POST':
        form = ClasseForm(request.POST, instance=classe)
        if form.is_valid():
            form.save()
            messages.success(request, "Classe modifiée avec succès !")
            return redirect('liste_classes')
        else:
            messages.error(request, "Erreur dans le formulaire. Veuillez corriger les erreurs.")
    else:
        form = ClasseForm(instance=classe)

    context = {
        'form': form,
        'classe': classe,
        'enseignants': Enseignant.objects.all()
    }
    return render(request, 'APP_G2S/composant-admin/modifier_classe.html', context)


@administrateur_required
def liste_classes(request):
    classes = Classe.objects.all().select_related('responsable')
    return render(request, 'APP_G2S/composant-admin/liste_classes.html', {
        'classes': classes
    })


@administrateur_required
def ajouter_matiere(request):
    if request.method == 'POST':
        form = MatiereForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Matière ajoutée avec succès !")
            return redirect('liste_matieres')
    else:
        form = MatiereForm()

    return render(request, 'APP_G2S/composant-admin/ajouter_matiere.html', {'form': form})

@administrateur_required
def liste_matieres(request):
    matieres = Matiere.objects.all().prefetch_related('classe_set')
    print(matieres)
    print()
    return render(request, 'APP_G2S/composant-admin/liste_matiere.html', {
        'matieres': matieres
    })

@require_GET
def api_matieres(request):
    classe_id = request.GET.get('classe_id')
    if classe_id:
        matieres = Matiere.objects.filter(classe__id=classe_id).values('id', 'nom')
        return JsonResponse(list(matieres), safe=False)
    return JsonResponse([], safe=False)

@administrateur_required
def saisir_notes_examen(request, examen_id):
    examen = get_object_or_404(Examen, id=examen_id)
    eleves = Eleve.objects.filter(classe=examen.classe)

    if request.method == 'POST':
        for eleve in eleves:
            note = request.POST.get(f'note_{eleve.id}')
            try:
                note_value = float(note)
                if not (0 <= note_value <= 40):
                    messages.error(request, f"Note invalide pour {eleve.nom}")
                    continue
            except ValueError:
                messages.error(request, f"Valeur numérique invalide pour {eleve.nom}")
                continue
            if note:
                NoteExamen.objects.update_or_create(
                    eleve=eleve,
                    examen=examen,
                    defaults={'note': float(note)}
                )
        messages.success(request, "Notes enregistrées avec succès !")
        return redirect('detail_examen', examen_id=examen.id)

    return render(request, 'APP_G2S/composant-admin/saisir_notes.html', {
        'examen': examen,
        'eleves': eleves
    })


@administrateur_required
def logout_view(request):
    logout(request)
    return redirect('connexion_admin')


@administrateur_required
def creer_periode(request):
    if request.method == 'POST':
        form = PeriodePaiementForm(request.POST)
        if form.is_valid():
            try:
                periode = form.save()
                messages.success(request, "Période de paiement créée avec succès !")
                return redirect('gerer_paiements')
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PeriodePaiementForm()

    return render(request, 'APP_G2S/composant-admin/ajouter_periode_paie.html', {
        'form': form,
        'classes': Classe.objects.all(),
        'examens': Examen.objects.filter(validite='EN_COURS')
    })

@require_GET
def charger_donnees_eleve(request, eleve_id):
    try:
        eleve = Eleve.objects.get(id=eleve_id)
    except Eleve.DoesNotExist:
        return JsonResponse({'error': 'Élève non trouvé'}, status=404)
    matieres = Matiere.objects.filter(classe=eleve.classe)

    matieres_data = []
    for matiere in matieres:
        note = Note.objects.filter(eleve=eleve, matiere=matiere).first()
        matieres_data.append({
            'id': matiere.id,
            'nom': matiere.nom,
            'coefficient': matiere.coefficient,
            'note_existante': note.valeur if note else None
        })

    return JsonResponse({
        'eleve': {
            'nom': eleve.nom,
            'prenom': eleve.prenom,
            'classe': str(eleve.classe),
            'telephone': str(eleve.telephone),
            'residence': eleve.residence
        },
        'matiere': matieres_data,
        # 'appreciation': eleve.appreciation_generale
    })


@require_GET
def get_matieres_par_classe(request):
    eleve_id = request.GET.get('eleve_id')
    try:
        eleve = Eleve.objects.get(id=eleve_id)
        matieres = Matiere.objects.filter(classe=eleve.classe).distinct().values('id', 'nom', 'coefficient')
        return JsonResponse(list(matieres), safe=False)
    except Eleve.DoesNotExist:
        return JsonResponse([], safe=False)


@administrateur_required
def modifier_statut_examen(request, examen_id):
    examen = get_object_or_404(Examen, id=examen_id)

    if request.user.role not in ['DIRECTEUR', 'CENSEUR']:
        return HttpResponseForbidden("Permission refusée")

    if request.method == 'POST':
        nouveau_statut = request.POST.get('validite')
        if nouveau_statut in ['EN_COURS', 'FIN']:
            examen.validite = nouveau_statut
            examen.save()
            messages.success(request, "Statut de l'examen mis à jour")
            return redirect('liste_examens')

    return render(request, 'APP_G2S/composant-admin/modifier_statut_examen.html', {
        'examen': examen
    })


@administrateur_required
def liste_absences(request):
    absences = Absence.objects.select_related('eleve', 'emploi_du_temps').order_by('-date')

    # Filtres
    eleve_id = request.GET.get('eleve')
    date = request.GET.get('date')

    if eleve_id:
        absences = absences.filter(eleve__id=eleve_id)
    if date:
        absences = absences.filter(date=date)

    context = {
        'absences': absences,
        'eleves': Eleve.objects.all(),
    }
    return render(request, 'APP_G2S/composant-admin/liste_absences.html', context)


@administrateur_required
def ajouter_absence(request):
    if request.method == 'POST':
        form = AbsenceForm(request.POST)
        if form.is_valid():
            try:
                absence = form.save(commit=False)
                absence.date = absence.emploi_du_temps.date
                absence.save()
                message = (
                    f"Alerte absence : {absence.eleve} absent(e) le {absence.date.strftime('%d/%m')} "
                    f"en {absence.emploi_du_temps.matiere.nom}. "
                    f"Justification : {request.POST.get('url') or request.META.get('HTTP_REFERER') or request.build_absolute_uri()}/absences/{absence.id}"
                )
                SMSService.send_sms(
                    numero=str(absence.eleve.telephone),
                    message=message
                )
                messages.success(request, "Absence enregistrée avec succès")
            except Exception as e:
                print(f"Erreur envoi SMS : {str(e)}")
                messages.error(request, f"Erreur : {str(e)}")
                logger.error(f"Erreur envoi SMS : {str(e)}")
        else:
            messages.error(request, "Formulaire invalide")
    else:
        form = AbsenceForm()

    return render(request, 'APP_G2S/composant-admin/ajouter_absence.html', {'form': form})


@administrateur_required
def supprimer_absence(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    if request.method == 'POST':
        absence.delete()
        messages.success(request, "Absence supprimée avec succès")
        return redirect('liste_absences')
    return render(request, 'APP_G2S/composant-admin/supprimer_absence.html', {'absence': absence})


@administrateur_required
def modifier_absence(request, absence_id):
    absence = get_object_or_404(Absence, id=absence_id)
    if request.method == 'POST':
        form = AbsenceForm(request.POST, instance=absence)
        if form.is_valid():
            form.save()
            messages.success(request, "Absence modifiée avec succès")
            return redirect('liste_absences')
    else:
        form = AbsenceForm(instance=absence)
    return render(request, 'APP_G2S/composant-admin/modifier_absence.html', {'form': form})

def generer_recu_paiement(paiement):
    response = HttpResponse(content_type='application/pdf')
    filename = f"reçu_paiement_{paiement.id}_{paiement.date_paiement.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # En-tête de l'établissement
    story.append(Paragraph("ÉCOLE SECONDAIRE EXCELLENCE", styles['Title']))
    story.append(Paragraph("123 Avenue du Savoir, Ville", styles['Normal']))
    story.append(Paragraph("Tél: +223 00 00 00 00", styles['Normal']))
    story.append(Spacer(1, 12))

    # Contenu du reçu
    content = [
        f"Reçu N°: {paiement.id}",
        f"Date: {paiement.date_paiement.strftime('%d/%m/%Y %H:%M')}",
        f"Élève: {paiement.eleve}",
        f"Classe: {paiement.eleve.classe.nom}",
        f"Montant: {paiement.montant_paye} €",
        f"Mode de paiement: {paiement.get_mode_paiement_display()}",
        f"Encaissé par: {paiement.encaisser_par.get_full_name() if paiement.encaisser_par else 'Système'}"
    ]

    for line in content:
        story.append(Paragraph(line, styles['BodyText']))
        story.append(Spacer(1, 5))

    doc.build(story)
    return response


@administrateur_required
@transaction.atomic
def enregistrer_paiement_especes(request, eleve_id=None):
    eleve = get_object_or_404(Eleve, id=eleve_id) if eleve_id else None
    context = {'daily_total': 0, 'transaction_count': 0}

    if request.method == 'POST':
        form = PaiementFormEspeces(request.POST)
        if form.is_valid():
            try:
                paiement = form.save(commit=False)
                paiement.mode_paiement = 'ESPECES'
                paiement.statut_paiement = 'REUSSI'
                paiement.encaisser_par = request.user

                # Validation financière
                periode = paiement.periode
                montant_du = periode.montant - eleve.total_paye_periode(periode)
                if paiement.montant_paye > montant_du:
                    raise ValidationError("Le montant dépasse le solde dû pour cette période")

                paiement.save()


                pdf_response = generer_recu_paiement(paiement)
                pdf_name = f"recu_{paiement.id}.pdf"


                paiement.receipt_pdf.save(pdf_name, ContentFile(pdf_response.content))

                messages.success(request, "Paiement enregistré avec succès")
                return redirect('enregistrer_paiement_especes', eleve_id=eleve.id)

            except ValidationError as e:
                messages.error(request, str(e))

    # Statistiques journalières
    today = timezone.now().date()
    context.update({
        'recent_payments': Paiement.objects.filter(
            date_paiement__date=today
        ).select_related('eleve', 'periode')[:10],
        'daily_total': Paiement.objects.filter(
            date_paiement__date=today
        ).aggregate(total=Sum('montant_paye'))['total'] or 0,
        'transaction_count': Paiement.objects.filter(
            date_paiement__date=today
        ).count(),
        'cancellation_count': Paiement.objects.filter(
            date_paiement__date=today,
            statut_paiement='ANNULE'
        ).count(),
        'last_transaction_id': Paiement.objects.latest('id').id if Paiement.objects.exists() else 0
    })

    return render(request, 'APP_G2S/composant-admin/paiement_especes.html', context)


@administrateur_required
def exporter_paiements_excel(request):
    paiements = Paiement.objects.select_related('eleve').filter(mode_paiement='ESPECES')

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="historique_paiements.xlsx"'

    wb = Workbook()
    ws = wb.active
    ws.title = "Paiements en espèces"

    # En-têtes
    columns = [
        'Date', 'Référence', 'Élève',
        'Classe', 'Montant', 'Encaisseur'
    ]
    ws.append(columns)

    # Style des en-têtes
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Données
    for p in paiements:
        ws.append([
            p.date_paiement.strftime('%d/%m/%Y %H:%M'),
            p.reference,
            p.eleve.nom,
            p.eleve.prenom,
            p.eleve.nom_parent,
            p.eleve.prenom_parent,
            p.eleve.classe.nom,
            p.montant_paye,
            p.encaisser_par.get_full_name() if p.encaisser_par else 'Système'
        ])

    wb.save(response)
    return response

@administrateur_required
def recherche_eleves(request):
    query = request.GET.get('q', '')
    eleves = Eleve.objects.filter(
        models.Q(nom__icontains=query) |
        models.Q(prenom__icontains=query) |
        models.Q(telephone__icontains=query)
    ).select_related('classe')[:10]

    results = [{
        'id': e.id,
        'nom_complet': f"{e.prenom} {e.nom}",
        'classe': str(e.classe),
        'solde': e.solde_restant,
        'url': reverse('enregistrer_paiement_especes', args=[e.id])
    } for e in eleves]

    return JsonResponse({'results': results})

@administrateur_required
def annuler_paiement(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)
    if paiement.mode_paiement == 'ESPECES':
        paiement.delete()
        messages.success(request, "Paiement en espèces annulé avec succès")
    return redirect('gerer_paiements')

@administrateur_required
def dashboard_paiements(request):
    # Gestion du formulaire de période de paiement
    periode_form = PeriodePaiementForm(request.POST or None)
    if request.method == 'POST' and 'submit_periode' in request.POST:
        if periode_form.is_valid():
            periode_form.save()
            messages.success(request, "Période créée avec succès!")
            return redirect('dashboard_paiements')

    # Gestion du formulaire de paiement en espèces
    paiement_form = PaiementFormEspeces(request.POST or None)
    if request.method == 'POST' and 'submit_paiement' in request.POST:
        if paiement_form.is_valid():
            paiement = paiement_form.save(commit=False)
            if paiement.eleve.classe != paiement.periode.classe:
                messages.error(request, "La période ne correspond pas à la classe de l'élève.")
            else:
                paiement.mode_paiement = 'ESPECES'
                paiement.statut_paiement = 'REUSSI'
                paiement.save()
                messages.success(request, "Paiement enregistré!")
                return redirect('dashboard_paiements')

    # Récupération des données
    periodes = PeriodePaiement.objects.all()
    paiements = Paiement.objects.select_related('eleve', 'periode').order_by('-date_paiement')[:10]

    context = {
        'periode_form': periode_form,
        'paiement_form': paiement_form,
        'periodes': periodes,
        'paiements': paiements,
    }
    return render(request, 'APP_G2S/composant-admin/dashboard_paiements.html', context)
@require_GET
def get_emplois(request):
    eleve_id = request.GET.get('eleve_id')
    try:
        eleve = Eleve.objects.get(id=eleve_id)
        emplois = EmploiDuTemps.objects.filter(classe=eleve.classe).values('id', 'date', 'matiere__nom')
        return JsonResponse(list(emplois), safe=False)
    except Eleve.DoesNotExist:
        return JsonResponse([], safe=False)

@csrf_exempt
def callback_paiement(request):
    # Logique de vérification des transactions Orange/Malitel
    if request.method == 'POST':
        data = json.loads(request.body)
        # Valider la transaction avec l'API mobile money
        # Mettre à jour le statut du paiement
        return JsonResponse({'status': 'success'})





@administrateur_required
def generer_pdf_absences(request):
    absences = Absence.objects.select_related('eleve', 'emploi_du_temps').order_by('-date')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_absences.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Rapport des Absences", styles['Title']))

    data = [['Élève', 'Date', 'Matière', 'Statut']]
    for absence in absences:
        data.append([
            f"{absence.eleve.prenom} {absence.eleve.nom}",
            absence.date.strftime("%d/%m/%Y"),
            absence.emploi_du_temps.matiere.nom,
            absence.get_justification_status_display()
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)
    return response




@administrateur_required
def exporter_excel_absences(request):
    absences = Absence.objects.select_related('eleve', 'emploi_du_temps').order_by('-date')
    print(absences)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="absences"du_{timezone.now()}.xlsx"'

    wb = Workbook()
    ws = wb.active
    ws.title = "Absences"

    columns = ['Élève', 'Date', 'Matière', 'Statut', 'Justificatif']
    ws.append(columns)

    for absence in absences:
        ws.append([
            f"{absence.eleve.prenom} {absence.eleve.nom}",
            absence.date,
            absence.emploi_du_temps.matiere.nom,
            absence.get_justification_status_display(),
            "Oui" if absence.justification_document else "Non"
        ])

    wb.save(response)
    return response



@administrateur_required
def choix_mode_paiement(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    periodes_impayees = PeriodePaiement.objects.filter(
        classe=eleve.classe,
        date_fin__lt=datetime.today()
    ).exclude(paiements__eleve=eleve)

    return render(request, 'APP_G2S/composant-admin/choix_paiement.html', {
        'eleve': eleve,
        'periodes_impayees': periodes_impayees
    })

# @transaction.atomic
@csrf_exempt
def initier_paiement_mobile(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        eleve_id = data['eleve_id']
        montant = data['montant']
        telephone = data['telephone']
        operator = data['operator']
        eleve = get_object_or_404(Eleve, id=eleve_id)

        try:
            if operator == 'ORANGE':
                response = OrangeMoneyAPI.initier_paiement(montant, telephone)
            elif operator == 'MALITEL':
                response = MalitelMoneyAPI.initier_paiement(montant, telephone)
            else:
                return JsonResponse({'status': 'error', 'message': 'Opérateur invalide'})

            # Enregistrer la transaction en base
            Paiement.objects.create(
                eleve=eleve,
                periode_id=data['periode_id'],
                montant_paye=data['montant'],
                mode_paiement=data['operator'],
                statut_paiement='EN_ATTENTE'
            )
            return JsonResponse(response)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return HttpResponseForbidden()


@administrateur_required
def historique_paiements(request, eleve_id):
    paiements = Paiement.objects.select_related('eleve', 'periode').order_by('-date')
    eleve = get_object_or_404(Eleve, id=eleve_id)
    return render(request, 'APP_G2S/composant-admin/historique_paiements.html', {
        'paiements': paiements,
        'eleve': eleve
    })

