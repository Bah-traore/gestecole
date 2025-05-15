def tenant_context(request):
    """
    Context processor that adds the current tenant to the template context.
    """
    tenant = getattr(request, 'tenant', None)
    return {
        'current_tenant': tenant,
        'is_multi_tenant_mode': True,
    }

def user_permissions(request):
    """
    Context processor that adds permission-related variables to the template context.
    """
    context = {}

    # Check if user is authenticated
    if not request.user.is_authenticated:
        return {
            'is_admin': False,
            'is_directeur': False,
            'is_censeur': False,
            'is_comptable': False,
            'is_surveillant': False,
            'can_add_class': False,
            'can_modify_class': False,
            'can_add_subject': False,
            'can_manage_schedule': False,
            'can_edit_schedule': False,
        }

    # Check if user is admin
    is_admin = hasattr(request.user, 'is_admin') and request.user.is_admin
    context['is_admin'] = is_admin

    # Check user role
    user_role = getattr(request.user, 'role', None)
    context['is_directeur'] = user_role == 'DIRECTEUR'
    context['is_censeur'] = user_role == 'CENSEUR'
    context['is_comptable'] = user_role == 'COMPTABLE'
    context['is_surveillant'] = user_role == 'SURVEILLANT'

    # Check if user belongs to specific groups
    try:
        from django.contrib.auth.models import Group
        context['in_directeur_group'] = request.user.groups.filter(name='DIRECTEUR').exists()
        context['in_censeur_group'] = request.user.groups.filter(name='CENSEUR').exists()
        context['in_comptable_group'] = request.user.groups.filter(name='COMPTABLE').exists()
        context['in_surveillant_group'] = request.user.groups.filter(name='SURVEILLANT').exists()
    except:
        context['in_directeur_group'] = False
        context['in_censeur_group'] = False
        context['in_comptable_group'] = False
        context['in_surveillant_group'] = False

    # Define permission variables based on roles
    context['can_add_class'] = is_admin or context['is_directeur'] or context['is_censeur'] or context['in_directeur_group'] or context['in_censeur_group']
    context['can_modify_class'] = is_admin or context['is_directeur'] or context['is_censeur'] or context['in_directeur_group'] or context['in_censeur_group']
    context['can_add_subject'] = is_admin or context['is_directeur'] or context['is_censeur'] or context['in_directeur_group'] or context['in_censeur_group']
    context['can_manage_schedule'] = is_admin or context['is_directeur'] or context['is_censeur'] or context['is_surveillant'] or context['in_directeur_group'] or context['in_censeur_group'] or context['in_surveillant_group']
    context['can_edit_schedule'] = is_admin or context['is_directeur'] or context['is_censeur'] or context['is_surveillant'] or context['in_directeur_group'] or context['in_censeur_group'] or context['in_surveillant_group']

    return context
