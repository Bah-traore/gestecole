from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Template filter to check if a user belongs to a specific group.
    Usage: {% if request.user|has_group:"DIRECTEUR" %}...{% endif %}
    """
    try:
        return Group.objects.get(name=group_name).user_set.filter(id=user.id).exists()
    except Group.DoesNotExist:
        return False

@register.filter(name='has_role')
def has_role(user, role_name):
    """
    Template filter to check if a user has a specific role.
    Usage: {% if request.user|has_role:"DIRECTEUR" %}...{% endif %}
    """
    if hasattr(user, 'role'):
        return user.role == role_name
    return False

@register.filter(name='has_any_role')
def has_any_role(user, role_names):
    """
    Template filter to check if a user has any of the specified roles.
    Usage: {% if request.user|has_any_role:"DIRECTEUR,CENSEUR" %}...{% endif %}
    """
    if not hasattr(user, 'role'):
        return False
    
    roles = [r.strip() for r in role_names.split(',')]
    return user.role in roles

@register.filter(name='is_admin')
def is_admin(user):
    """
    Template filter to check if a user is an admin.
    Usage: {% if request.user|is_admin %}...{% endif %}
    """
    return hasattr(user, 'is_admin') and user.is_admin

@register.simple_tag(takes_context=True)
def can_access(context, *required_roles):
    """
    Template tag to check if a user has access based on required roles.
    Usage: {% can_access "DIRECTEUR" "CENSEUR" as has_access %}{% if has_access %}...{% endif %}
    """
    user = context['request'].user
    
    # Check if user is authenticated
    if not user.is_authenticated:
        return False
    
    # Check if user is admin
    if hasattr(user, 'is_admin') and user.is_admin:
        return True
    
    # Check if user has any of the required roles
    if hasattr(user, 'role') and user.role in required_roles:
        return True
    
    # Check if user belongs to any of the required groups
    for role in required_roles:
        try:
            if Group.objects.get(name=role).user_set.filter(id=user.id).exists():
                return True
        except Group.DoesNotExist:
            continue
    
    return False