import json

from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from APP_G2S.models import Periode, Classe, BulletinPerformance, Eleve, Note, NoteExamen, BulletinMatiere, logger
from gestecole.utils.calculatrice_bulletin import calculer_moyennes_coefficients, calculer_moyenne_generale
from gestecole.utils.decorateurs import administrateur_required


@administrateur_required

@transaction.atomic
def generate_bulletins(request):
    if request.method not in ['POST', 'GET']:  # Accepter GET et POST
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)

    try:
        # Récupération des paramètres selon la méthode
        if request.method == 'POST':
            data = json.loads(request.body)
        else:  # GET
            data = request.GET.dict()

        eleve_ids = data.get('eleve_ids', '') if 'eleve_ids' in data else []
        classe_id = data.get('classe_id')

        if not eleve_ids or not classe_id:
            return JsonResponse({'success': False, 'error': 'Données manquantes'}, status=400)

        # Récupération des données
        periode = Periode.objects.prefetch_related('classe').get(is_active=True)
        classe = Classe.objects.prefetch_related('matieres').get(id=classe_id)

        if periode.cloture:
            return JsonResponse({'success': False, 'error': 'Période clôturée'}, status=400)

        # Récupération des bulletins existants
        existing_bulletins = BulletinPerformance.objects.filter(
            eleve__in=eleve_ids,
            classes=classe,
            periode=periode
        ).select_related('eleve')

        existing_bulletin_map = {b.eleve_id: b for b in existing_bulletins}

        # Récupération des élèves avec leurs notes
        eleves = Eleve.objects.prefetch_related(
            Prefetch('notes_de_classe',
                    queryset=Note.objects.filter(periode=periode),
                     to_attr='notes_classe'),
            Prefetch('notes_examen',
                    queryset=NoteExamen.objects.filter(periode=periode),
                     to_attr='notes_exam')
        ).filter(id__in=eleve_ids)

        bulletins_to_update = []
        bulletins_to_create = []
        eleves_data = []


        def determiner_appreciation(moyenne):
            if moyenne >= 16: return "Excellent travail, continuez ainsi."
            elif moyenne >= 14: return "Très bon travail, vous êtes sur la bonne voie."
            elif moyenne >= 12: return "Bon travail, mais il y a encore des points à améliorer."
            elif moyenne >= 10: return "Travail passable, des efforts supplémentaires sont nécessaires."
            else: return "Insuffisant, il faut travailler beaucoup plus."

        # Calcul des nouvelles données

        for eleve in eleves:
            notes_classe = {n.matiere_id: n.valeur for n in eleve.notes_de_classe.all()}
            notes_examen = {n.matiere_id: n.note for n in eleve.notes_examen.all()}

            moyennes = calculer_moyennes_coefficients(notes_classe, notes_examen, classe.matieres.all())
            moyenne_generale = calculer_moyenne_generale(moyennes, classe.matieres.all())
            appreciation = determiner_appreciation(moyenne_generale)

            eleves_data.append({
                'eleve': eleve,
                'moyennes': moyennes,
                'moyenne_generale': moyenne_generale
            })

            # Gestion mise à jour/création
            if eleve.id in existing_bulletin_map:
                bulletin = existing_bulletin_map[eleve.id]
                bulletin.moyenne_generale = moyenne_generale
                bulletin.appreciation = appreciation
                bulletins_to_update.append(bulletin)
            else:
                bulletins_to_create.append(BulletinPerformance(
                    eleve=eleve,
                    classes=classe,
                    periode=periode,
                    moyenne_generale=moyenne_generale,
                    appreciation=appreciation,
                ))

        # Opérations bulk
        if bulletins_to_update:
            BulletinPerformance.objects.bulk_update(bulletins_to_update, ['moyenne_generale', 'appreciation'])

        if bulletins_to_create:
            BulletinPerformance.objects.bulk_create(bulletins_to_create)

        # Récupération de tous les bulletins concernés
        all_bulletins = BulletinPerformance.objects.filter(
            eleve__in=eleve_ids,
            classes=classe,
            periode=periode
        )

        # Suppression des anciennes relations matières
        BulletinMatiere.objects.filter(bulletin__in=all_bulletins).delete()

        # Création des nouvelles relations matières
        bulletin_matieres = []
        eleve_data_map = {data['eleve'].id: data for data in eleves_data}

        for bulletin in all_bulletins:
            data = eleve_data_map[bulletin.eleve_id]
            for matiere in classe.matieres.all():
                bulletin_matieres.append(BulletinMatiere(
                    bulletin=bulletin,
                    matiere=matiere,
                    note=data['moyennes'].get(matiere.id, 0.0)
                ))

        BulletinMatiere.objects.bulk_create(bulletin_matieres)

        return JsonResponse({
            'success': True,
            'updated': len(bulletins_to_update),
            'created': len(bulletins_to_create),
            'message': f'{len(all_bulletins)} bulletin(s) mis à jour/généré(s)'
        })

    except Exception as e:
        logger.error(f"Erreur génération bulletins: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

