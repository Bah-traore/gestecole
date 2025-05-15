from django.db.models import Model, QuerySet
from django.http import HttpRequest

from gestecole.utils.tenant import get_current_tenant


def get_tenant_from_request(request):
    """
    Récupère le tenant à partir de la requête.
    
    Args:
        request: L'objet HttpRequest
        
    Returns:
        Le tenant actuel ou None si aucun tenant n'est défini
    """
    return getattr(request, 'tenant', None)

def tenant_filter(queryset, request):
    """
    Filtre un queryset pour ne retourner que les objets appartenant au tenant actuel.
    
    Args:
        queryset: Le queryset à filtrer
        request: L'objet HttpRequest contenant le tenant
        
    Returns:
        Un queryset filtré par tenant
    """
    tenant = get_tenant_from_request(request)
    
    if tenant is None:
        return queryset
    
    # Vérifier si le modèle a un champ tenant
    model = queryset.model
    if hasattr(model, 'tenant'):
        return queryset.filter(tenant=tenant)
    
    return queryset

def tenant_aware(view_func):
    """
    Décorateur pour rendre une vue compatible avec le multi-tenant.
    Filtre automatiquement les querysets passés à la vue.
    
    Args:
        view_func: La fonction de vue à décorer
        
    Returns:
        Une fonction de vue décorée qui filtre les querysets par tenant
    """
    def wrapper(request, *args, **kwargs):
        # Exécuter la vue originale
        response = view_func(request, *args, **kwargs)
        
        # Si la réponse est un dictionnaire (pour un template)
        if isinstance(response, dict):
            # Parcourir les éléments du dictionnaire
            for key, value in response.items():
                # Si c'est un queryset, le filtrer par tenant
                if isinstance(value, QuerySet):
                    response[key] = tenant_filter(value, request)
        
        return response
    
    return wrapper

def tenant_context(request):
    """
    Context processor qui ajoute des fonctions utilitaires liées au tenant au contexte.
    
    Args:
        request: L'objet HttpRequest
        
    Returns:
        Un dictionnaire contenant des fonctions utilitaires liées au tenant
    """

    return {
        'current_tenant': get_current_tenant(),
        'tenant_filter': lambda qs: qs.filter(tenant=get_current_tenant())
    }