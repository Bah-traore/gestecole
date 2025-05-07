from django import template

register = template.Library()

@register.filter
def ordinal_suffix(value):
    if value == 1:
        return f"{value}er"
    return f"{value}ème"