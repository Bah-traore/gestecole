import logging


# Calcul des moyennes coefficient pour chaque matière
def calculer_moyennes_coefficients(notes_cours, notes_examens, matieres_classe):
    # moyennes_coefficient = {}
    # for matiere in matieres_classe:
    #     note_cours = next((n.valeur for n in notes_cours if n.matiere.id == matiere.id), 0)
    #     note_examen = next((n.note for n in notes_examens if n.matiere.id == matiere.id), 0)
    #
    #     # Calcul de la moyenne coefficient
    #     moyenne_coeff = ((note_cours + (note_examen * 2)) / 3) * matiere.coefficient
    #     moyennes_coefficient[matiere.id] = round(moyenne_coeff, 3)
    #     print(moyennes_coefficient, moyenne_coeff)
    # print(moyennes_coefficient)
    # logger = logging.getLogger(__name__)
    #
    # logger.debug(f"Moyennes coefficients: {moyennes_coefficient}")
    #
    # return moyennes_coefficient

    moyennes_coefficient = {}
    for matiere in matieres_classe:
        # Accès direct aux valeurs via l'ID matière
        note_cours = notes_cours.get(matiere.id, 0)
        # note_cours = notes_cours.filter(id=matiere.id).first() or 0
        # note_examen = notes_examens.filter(id=matiere.id).first() or 0
        note_examen = notes_examens.get(matiere.id, 0)

        # Calcul de la moyenne coefficient
        moyenne_coeff = ((note_cours + (note_examen * 2)) / 3) * matiere.coefficient
        moyennes_coefficient[matiere.id] = round(moyenne_coeff, 3)

    from APP_G2S.models import logger

    logger.debug(f"Moyennes coefficients: {moyennes_coefficient}")
    return moyennes_coefficient



def calculer_moyenne_generale(moyennes_coefficient, matieres_classe):
    total_points = sum(moyennes_coefficient.values())
    total_coefficients = sum(m.coefficient for m in matieres_classe)
    print(total_points, total_coefficients)
    moyenne_generale = total_points / total_coefficients if total_coefficients > 0 else 0.0
    return round(moyenne_generale, 3)
