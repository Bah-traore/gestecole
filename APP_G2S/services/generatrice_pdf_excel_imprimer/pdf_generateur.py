from functools import partial
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.http import HttpResponse
from django.utils import timezone
import settings
from APP_G2S.models import Absence, Matiere, Eleve, Enseignant, BulletinPerformance, Classe, Note, NoteExamen
from APP_G2S.services.periodique.file_genereale import FiltreService
from gestecole.utils.decorateurs import administrateur_required
import os

LOGO_PATH = os.path.join(settings.BASE_DIR, 'gestecole/APP_G2S/static/logo_essaie.png')


# Configuration commune de l'en-tête et pied de page
def header_footer(canvas, doc, bulletin=None):
    canvas.saveState()
    width, height = letter

    # Logo
    if os.path.exists(LOGO_PATH):
        canvas.drawImage(LOGO_PATH, 40, height - 60, width=100, height=100, preserveAspectRatio=True, mask='auto')

    # Infos école
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(220, height - 0, "Ecole PERMANANT")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(180, height - 15, "123, Rue de l'Education, Kalaban-coura, Mali/Bamako")
    canvas.drawString(180, height - 25, "Tel: 94 30 63 02 | Email: contact@permanant.edu")

    if bulletin:
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(240, height - 60, f"Bulletin de {bulletin.eleve.nom} {bulletin.eleve.prenom}")


    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(40, 30, f"Rapport généré par GESTECOLE - © {timezone.now().date()} Ecole PERMANANT")
    canvas.drawRightString(width - 40, 30, f"Page {doc.page}")
    canvas.restoreState()


# Style de tableau commun
def apply_common_table_style(table):
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
          ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
          ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
          ('FONTSIZE', (0, 0), (-1, 0), 11),
          ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
          ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e6f2ff')),
          ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
          ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f6fa')]),
          ]))

@administrateur_required
def generer_pdf_absences(request):
    """Génère le PDF des absences avec filtrage et affiche le niveau et la section de la classe"""
    # Récupérer les paramètres GET
    classe_id = request.GET.get('classe')
    annee = request.GET.get('annee')

    # Filtrer les classes selon l'année si précisé
    classes = FiltreService.get_classes(annee) if annee else Classe.objects.all()

    # Filtrer les absences
    absences = Absence.objects.select_related('eleve', 'emploi_du_temps', 'eleve__classe').filter(eleve__classe__in=classes)

    if classe_id and classe_id.isdigit():
        absences = absences.filter(eleve__classe__id=int(classe_id))

    # Générer le PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'absences_{timezone.now().date()}.pdf'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=35,
        rightMargin=35,
        topMargin=100,
        bottomMargin=50
    )

    elements = []
    styles = getSampleStyleSheet()

    # Titre avec filtres appliqués
    title = "Rapport des Absences"
    if classe_id or annee:
        title += " (Filtré)"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    # Afficher niveau et section si une classe est sélectionnée
    if classe_id and classe_id.isdigit():
        try:
            classe = Classe.objects.get(id=int(classe_id))
            niveau = getattr(classe, 'niveau', 'N/A')
            section = getattr(classe, 'section', 'N/A')
            # Affichage horizontal des infos Classe, Niveau, Section
            info_row = [
                Paragraph(f"<b>Classe :</b> {classe}", styles['Normal']),
                Paragraph(f"<b>Niveau :</b> {niveau}", styles['Normal']),
                Paragraph(f"<b>Section :</b> {section}", styles['Normal']),
            ]
            info_table = Table([info_row], colWidths=[120, 120, 120])
            elements.append(info_table)
            # Afficher tous les niveaux de la classe si c'est une relation multiple
            if hasattr(classe, 'niveau'):
                niveau_attr = getattr(classe, 'niveau')
                if hasattr(niveau_attr, 'all'):
                    niveau_str = ", ".join(str(n) for n in niveau_attr.all())
                else:
                    niveau_str = str(niveau_attr)
                elements.append(Paragraph(f"<b>Niveaux de la classe :</b> {niveau_str}", styles['Normal']))
            elements.append(Spacer(1, 8))
        except Classe.DoesNotExist:
            pass

    # Données
    data = [['Élève', 'Date', 'Matière', 'Statut', 'classe']]
    for absence in absences:
        data.append([
            f"{absence.eleve.prenom} {absence.eleve.nom}",
            absence.date.strftime("%d/%m/%Y"),
            absence.emploi_du_temps.matiere.nom,
            absence.get_justification_status_display(),
            str(absence.eleve.classe)
        ])

    table = Table(data, colWidths=[120, 70, 120, 80])
    apply_common_table_style(table)
    elements.append(table)

    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return response


@administrateur_required
def generer_pdf_eleves(request):
    """Génère le PDF de la liste des élèves"""
    # On ne filtre pas par année/classe si les paramètres ne sont pas fournis
    try:
        eleves = Eleve.objects.all().select_related('classe')
    except ValueError as ve:
        return HttpResponse(f"Erreur de valeur: {ve}", status=400)
    except AttributeError as ae:
        return HttpResponse(f"Erreur d'attribut: {ae}", status=500)
    except Exception as e:
        return HttpResponse(f"Erreur inattendue: {e}", status=500)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'liste_eleves_{timezone.now().date()}.pdf'



    doc = SimpleDocTemplate(response, pagesize=A4,
        leftMargin=35,
        rightMargin=35,
        topMargin=100,
        bottomMargin=50)

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Liste des Élèves", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [['Nom', 'Prénom', 'Classe', 'Téléphone', 'Résidence']]
    for eleve in eleves:
        try:
            data.append([
                eleve.nom,
                eleve.prenom,
                str(eleve.classe),
                eleve.telephone,
                eleve.residence
            ])
        except Exception as e:
            # Ajoute une ligne d'erreur pour l'élève problématique
            data.append([f"Erreur: {e}", "", "", "", ""])

    table = Table(data, colWidths=[100, 100, 80, 90, 120])
    apply_common_table_style(table)
    elements.append(table)

    doc.build(
        elements,
        onFirstPage=partial(header_footer),
        onLaterPages=partial(header_footer)
    )
    return response 


@administrateur_required
def generer_pdf_matieres(request):
    """Génère le PDF de la liste des matières"""
    matieres = Matiere.objects.all().prefetch_related('classe_set')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'liste_matieres_{timezone.now().date()}.pdf'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=35,
        rightMargin=35,
        topMargin=100,
        bottomMargin=50
    )

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Liste des Matières", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [['Matière', 'Classes Associées', 'Coefficient']]
    for matiere in matieres:
        classes = ", ".join(c.nom for c in matiere.classe_set.all())
        data.append([matiere.nom, classes, str(matiere.coefficient)])

    table = Table(data, colWidths=[150, 150, 60])
    apply_common_table_style(table)
    elements.append(table)

    doc.build(
        elements,
        onFirstPage=partial(header_footer),
        onLaterPages=partial(header_footer)
    )
    return response

@administrateur_required
def generer_pdf_bulletins(request):
    bulletin_id = request.GET.get('bulletin_id')
    if not bulletin_id or not bulletin_id.isdigit():
        return HttpResponse("Bulletin introuvable", status=404)

    try:
        bulletin = BulletinPerformance.objects.select_related(
            'eleve', 'periode', 'eleve__classe'
        ).get(id=int(bulletin_id))
    except (BulletinPerformance.DoesNotExist, ValueError):
        return HttpResponse("Bulletin introuvable", status=404)

    # Récupération des matières avec vérification
    matieres = bulletin.classes.matieres.all()
    if not matieres.exists():
        return HttpResponse("Aucune matière trouvée pour cette classe", status=400)

    # Préparation des données du tableau
    data = [
        [
            Paragraph("<b>Matière</b>", getSampleStyleSheet()['Heading4']),
            Paragraph("<b>Coeff.</b>", getSampleStyleSheet()['Heading4']),
            Paragraph("<b>Note Classe</b>", getSampleStyleSheet()['Heading4']),
            Paragraph("<b>Note Examen</b>", getSampleStyleSheet()['Heading4']),
            Paragraph("<b>Moyenne</b>", getSampleStyleSheet()['Heading4'])
        ]
    ]

    total_points = 0
    total_coeff = 0

    for matiere in matieres:
        # Récupération des notes avec gestion des erreurs
        try:
            note_classe = Note.objects.get(
                eleve=bulletin.eleve,
                matiere=matiere,
                periode=bulletin.periode
            ).valeur
        except Note.DoesNotExist:
            note_classe = 0.0

        try:
            note_examen = NoteExamen.objects.get(
                eleve=bulletin.eleve,
                matiere=matiere,
                periode=bulletin.periode
            ).note
        except NoteExamen.DoesNotExist:
            note_examen = 0.0

        # Calcul de la moyenne matière
        moyenne_matiere = (note_classe + 2 * note_examen) / 3
        total_points += moyenne_matiere * matiere.coefficient
        total_coeff += matiere.coefficient

        data.append([
            matiere.nom,
            str(matiere.coefficient),
            f"{note_classe:.2f}" if note_classe else "-",
            f"{note_examen:.2f}" if note_examen else "-",
            f"{moyenne_matiere:.2f}" if moyenne_matiere > 0 else "0.00"
        ])

    # Calcul de la moyenne générale
    moyenne_generale = total_points / total_coeff if total_coeff > 0 else 0.0
    bulletin.moyenne_generale = moyenne_generale
    bulletin.save()

    # Ligne de moyenne générale
    data.append([
        Paragraph("<b>TOTAL / MOYENNE GÉNÉRALE</b>", getSampleStyleSheet()['Heading4']),
        "", "", "",
        Paragraph(f"<b>{moyenne_generale:.2f}/20</b>", getSampleStyleSheet()['Heading4'])
    ])

    # Création du PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"bulletin_{bulletin.eleve.nom}_{bulletin.periode.numero}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=35,
        rightMargin=35,
        topMargin=100,
        bottomMargin=50
    )

    elements = []
    styles = getSampleStyleSheet()
    elements.append(Spacer(1, 20))

    # Informations période/classe
    infos_periode = [
        Paragraph(f"<b>Période:</b> {bulletin.periode.numero} ({bulletin.periode.annee_scolaire})", styles['BodyText']),
        Paragraph(f"<b>Classe:</b> {bulletin.classes.niveau} {bulletin.classes.section}", styles['BodyText'])
    ]
    elements.append(Table([infos_periode], colWidths=[doc.width/2]*2))
    elements.append(Spacer(1, 30))

    # Création du tableau principal
    table = Table(data, colWidths=[doc.width*0.35, doc.width*0.15, doc.width*0.2, doc.width*0.2, doc.width*0.2])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#DDDDDD')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#d9ead3')),
        ('ROWBREAK', (0,-1), (-1,-1)),
    ]))
    elements.append(table)

    # Section appréciation
    elements.append(Spacer(1, 25))
    appreciation_style = ParagraphStyle(
        'Appreciation',
        parent=styles['BodyText'],
        fontSize=12,
        backColor=colors.HexColor('#F8F8F8'),
        borderPadding=10,
        leading=16
    )
    elements.append(Paragraph("<b>APPRÉCIATION :</b>", styles['Heading3']))
    elements.append(Paragraph(bulletin.appreciation or "Aucune appréciation disponible.", appreciation_style))


    doc.build(
        elements,
        onFirstPage=partial(header_footer, bulletin=bulletin),
        onLaterPages=partial(header_footer, bulletin=bulletin)
    )
    
    return response


def generateur_pdf_paiement(request, paiement):
    pass