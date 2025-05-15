from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.http import HttpResponse
from django.utils import timezone

import settings
from APP_G2S.models import Absence
from gestecole.utils.decorateurs import administrateur_required
import os
# /home/bah/Bureau/gestecole/APP_G2S/static
LOGO_PATH = os.path.join(settings.BASE_DIR, 'gestecole/APP_G2S/static/logo_essaie.png')
if os.path.exists(LOGO_PATH):
    print('ok')
else:
    print("non")
print(LOGO_PATH)
def header_footer(canvas, doc):
    # Header
    canvas.saveState()
    width, height = letter

    # Logo
    logo_width = 80
    logo_height = 80
    if os.path.exists(LOGO_PATH):
        canvas.drawImage(LOGO_PATH, 40, height - 100, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
    # Infos école
    school_name = "Ecole PERMANANT"
    school_address = "123, Rue de l'Education, Kalaban-coura, Mali/Bamako"
    school_contact = "Tel: 94 30 63 02 | Email: contact@permanant.edu"
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(120, height - 50, school_name)
    canvas.setFont("Helvetica", 10)
    canvas.drawString(120, height - 65, school_address)
    canvas.drawString(120, height - 80, school_contact)

    # Footer
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(40, 30, f"Rapport généré par GESTECOLE - © {timezone.now().date()} Ecole PERMANANT")
    canvas.drawRightString(width - 40, 30, f"Page {doc.page}")
    canvas.restoreState()

@administrateur_required
def generer_pdf_absences(request):
    classe = request.GET('classe_id')
    absences = Absence.objects.select_related('eleve', 'emploi_du_temps').order_by('-date')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_absences{timezone.now().date()}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter,
                            leftMargin=40, rightMargin=40, topMargin=110, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()
    print(styles)
    title_style = styles['Title']
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=6,
        textColor=colors.darkblue
    )

    elements.append(Paragraph("Rapport des Absences", title_style))
    elements.append(Spacer(1, 12))

    # Si on veut générer pour un élève spécifique, sinon on affiche pour tous
    if absences.exists():
        eleve = absences[0].eleve
        infos = [
            f"<b>Nom:</b> {eleve.nom}",
            f"<b>Prénom:</b> {eleve.prenom}",
            f"<b>Classe:</b> {getattr(eleve, 'classe', 'N/A')}",
            f"<b>Matricule:</b> {getattr(eleve, 'matricule', 'N/A')}",
        ]
        for info in infos:
            elements.append(Paragraph(info, info_style))
        elements.append(Spacer(1, 12))

    data = [['Élève', 'Date', 'Matière', 'Statut']]
    for absence in absences:
        data.append([
            f"{absence.eleve.prenom} {absence.eleve.nom}",
            absence.date.strftime("%d/%m/%Y"),
            absence.emploi_du_temps.matiere.nom,
            absence.get_justification_status_display()
        ])

    table = Table(data, hAlign='CENTER', colWidths=[120, 70, 120, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 13),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#e6f2ff')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f6fa')]),
    ]))

    elements.append(table)
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return response



@administrateur_required
def generer_pdf_eleves(request):
    # Récupération des paramètres de filtrage
    annee = request.GET.get('annee')
    classe_id = request.GET.get('classe_id')
    
    classes = FiltreService.get_classes(annee)
    eleves = Eleve.objects.filter(classe__in=classes)
    if classe_id and classe_id.isdigit():
        eleves = eleves.filter(classe__id=int(classe_id))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="liste_eleves_{timezone.now().date()}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter,
                            leftMargin=40, rightMargin=40, topMargin=110, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titre
    title_style = styles['Title']
    elements.append(Paragraph("Liste des Élèves", title_style))
    elements.append(Spacer(1, 12))

    # Tableau
    data = [['Nom', 'Prénom', 'Classe', 'Téléphone', 'Résidence']]
    for eleve in eleves:
        data.append([
            eleve.nom,
            eleve.prenom,
            str(eleve.classe),
            eleve.telephone,
            eleve.residence
        ])

    table = Table(data, colWidths=[100, 100, 80, 90, 120])
    apply_common_table_style(table)
    elements.append(table)
    
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return response

@administrateur_required
def generer_pdf_enseignants(request):
    enseignants = Enseignant.objects.all().prefetch_related('matieres')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="liste_enseignants_{timezone.now().date()}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter,
                            leftMargin=40, rightMargin=40, topMargin=110, bottomMargin=50)
    elements = []
    
    elements.append(Paragraph("Liste des Enseignants", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [['Nom', 'Prénom', 'Matières', 'Téléphone']]
    for enseignant in enseignants:
        matieres = ", ".join([m.nom for m in enseignant.matieres.all()])
        data.append([
            enseignant.nom,
            enseignant.prenom,
            matieres,
            enseignant.telephone
        ])

    table = Table(data, colWidths=[100, 100, 150, 90])
    apply_common_table_style(table)
    elements.append(table)
    
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return response

@administrateur_required
def generer_pdf_bulletins(request):
    periode_id = request.GET.get('periode_id')
    bulletins = BulletinPerformance.objects.select_related('eleve', 'periode')
    if periode_id:
        bulletins = bulletins.filter(periode__id=periode_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="liste_bulletins_{timezone.now().date()}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    
    elements.append(Paragraph("Liste des Bulletins", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [['Élève', 'Classe', 'Moyenne', 'Période']]
    for bulletin in bulletins:
        data.append([
            f"{bulletin.eleve.prenom} {bulletin.eleve.nom}",
            str(bulletin.eleve.classe),
            str(bulletin.moyenne_generale),
            bulletin.periode.nom
        ])

    table = Table(data, colWidths=[120, 80, 60, 100])
    apply_common_table_style(table)
    elements.append(table)
    
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return response

@administrateur_required
def generer_pdf_matieres(request):
    matieres = Matiere.objects.all().prefetch_related('classe_set')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="liste_matieres_{timezone.now().date()}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    
    elements.append(Paragraph("Liste des Matières", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [['Matière', 'Classes', 'Coefficient']]
    for matiere in matieres:
        classes = ", ".join([c.nom for c in matiere.classe_set.all()])
        data.append([
            matiere.nom,
            classes,
            str(matiere.coefficient)
        ])

    table = Table(data, colWidths=[150, 150, 60])
    apply_common_table_style(table)
    elements.append(table)
    
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return response

def apply_common_table_style(table):
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#e6f2ff')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f2f6fa')]),
    ]))
