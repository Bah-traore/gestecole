import json

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods

from APP_G2S.models import Examen, Classe, logger, Eleve, Periode, Note, NoteExamen, Matiere
from gestecole.utils.calculatrice_bulletin import calculer_moyennes_coefficients, calculer_moyenne_generale
from gestecole.utils.decorateurs import administrateur_required


@administrateur_required
@require_GET
def get_eleves_par_classe(request):
    classe_id = request.GET.get('classe_id')
    print(classe_id)
    if not classe_id:
        return JsonResponse({'error': 'Paramètre classe_id manquant'}, status=400)

    try:
        eleves = Eleve.objects.filter(classe__id=classe_id).values('id', 'prenom', 'nom', 'identifiant')
        return JsonResponse({
            'eleves': list(eleves),
            'count': eleves.count()
        })
    except Eleve.DoesNotExist:
        return JsonResponse({'error': 'Classe non trouvée'}, status=404)





@administrateur_required
@require_GET
def get_eleves_classe(request):
    eleve_id = request.GET.get('eleve_id')
    classe_id = request.GET.get('classe_id')

    try:
        # Validation des paramètres obligatoires
        if not classe_id:
            raise ValidationError("L'ID de la classe est requis")

        # Récupération des objets avec gestion des erreurs
        classe = Classe.objects.get(id=classe_id)
        matieres = classe.matieres.all()

        # Vérification de la période active
        periode = Periode.objects.active().first()
        if not periode:
            raise ValidationError("Aucune période active disponible")

        # Vérifier si la période est clôturée
        if periode.cloture:
            return JsonResponse({'error': 'La période est clôturée, consultation impossible'}, status=403)

        # Récupération de l'examen lié à la période
        examen = Examen.objects.filter(
            classe=classe,
            periode=periode,
            validite="EN_COURS",
            date__range=(periode.date_debut, periode.date_fin)
        ).first()
        # Optimisation des requêtes de notes
        eleves_query = Eleve.objects.filter(classe=classe).prefetch_related(
            Prefetch(
                'notes_de_classe',
                queryset=Note.objects.filter(periode=periode, examen_reference=examen),
                to_attr='notes_classe'
            ),
            Prefetch(
                'notes_examen',
                queryset=NoteExamen.objects.filter(examen=examen, periode=periode),
                to_attr='notes_exam'
            )
        )
        print('eleves_query', eleves_query)
        if eleve_id:
            eleves_query = eleves_query.filter(id=eleve_id)

        # Construction des données
        eleves_data = []
        for eleve in eleves_query:
            notes_data = []
            print(eleve)

            # Préparation des notes en dictionnaire pour accès rapide
            notes_classe = {note.matiere_id: note.valeur for note in eleve.notes_classe}
            notes_examen = {note.matiere_id: note.note for note in eleve.notes_exam}

            moyennes_coefficient = calculer_moyennes_coefficients(
                notes_classe,
                notes_examen,
                matieres
            )
            print(moyennes_coefficient)
            moyenne_generale = calculer_moyenne_generale(moyennes_coefficient, matieres)

            for matiere in matieres:
                note_classe = notes_classe.get(matiere.id)
                note_examen = notes_examen.get(matiere.id)


                notes_data.append({
                    'matiere_id': matiere.id,
                    'matiere_nom': matiere.nom,
                    'classe_note': note_classe,
                    'examen_note': note_examen,
                    'coefficient': matiere.coefficient,
                    'moyenne_coefficient': moyennes_coefficient.get(matiere.id, 0),
                    'max_note': 20.0
                })

            eleves_data.append({
                'id': eleve.id,
                'nom': eleve.nom,
                'prenom': eleve.prenom,
                'telephone': eleve.telephone.as_international,
                'residence': eleve.residence,
                'notes': notes_data,
                'moyenne_generale': moyenne_generale,
                'max_note': 20.0
            })

        return JsonResponse({
            'classe': str(classe),
            'periode': str(periode),
            'eleves': eleves_data,
            'statut_examen': examen.validite if examen else None
        }, safe=False)

    except Classe.DoesNotExist:
        return JsonResponse({'error': 'Classe introuvable'}, status=404)
    except Examen.DoesNotExist:
        return JsonResponse({'error': 'Examen introuvable'}, status=404)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Erreur serveur: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Erreur interne du serveur'}, status=500)



@require_GET
def get_eleves(request):
    classe_id = request.GET.get('classe_id')
    if classe_id:
        eleves = Eleve.objects.filter(classe__id=classe_id).values('id', 'nom', 'prenom')
        return JsonResponse(list(eleves), safe=False)
    return JsonResponse([], safe=False)
