import re
from django.utils.safestring import mark_safe
from django import template
register = template.Library()
from django import template
from reportlab.graphics.barcode.qrencoder import unicode

from APP_G2S.models import Periode, Note, NoteExamen

register = template.Library()

@register.filter
def get_note(notes, matiere_id):
    try:
        return next(note.valeur for note in notes if note.matiere.id == matiere_id)
    except StopIteration:
        return ""


@register.filter(name='filter_matiere_classe')
def filter_matiere_classe(notes, matiere):
    try:
        return notes.get(matiere=matiere).valeur
    except (Note.DoesNotExist, AttributeError):
        return 0.0

@register.filter(name='filter_matiere_examen')
def filter_matiere_examen(notes, matiere):
    try:
        return notes.get(matiere=matiere).note*2
    except (NoteExamen.DoesNotExist, AttributeError):
        return 0.0

@register.filter
def get_periode_object(periode_id):
    try:
        return Periode.objects.get(pk=periode_id)
    except Periode.DoesNotExist:
        return None


@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key, "Valeur par défaut")


@register.filter
def get_classe_note(eleve, matiere):
    note = Note.objects.filter(
        eleve=eleve,
        matieres=matiere,
        examen__isnull=True
    ).first()
    return note.valeur if note else ''

@register.filter
def get_examen_note(eleve, examen):
    if not examen:
        return ''
    note = NoteExamen.objects.filter(
        eleve=eleve,
        examen=examen
    ).first()
    return note.note if note else ''

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, None)




class_re = re.compile(r'(?<=class=["\'])(.*)(?=["\'])')
@register.filter
def add_class(value, css_class):
    string = unicode(value)
    match = class_re.search(string)
    if match:
        m = re.search(r'^%s$|^%s\s|\s%s\s|\s%s$' % (css_class, css_class,
                                                    css_class, css_class),
                                                    match.group(1))
        print(match.group(1))
        if not m:
            return mark_safe(class_re.sub(match.group(1) + " " + css_class,
                                          string))
    else:
        return mark_safe(string.replace('>', ' class="%s">' % css_class))
    return value