import time
from django.conf import settings
from django.db import connection
from django.http import Http404
from APP_G2S.models import Tenant


class HierarchyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Vérifie si l'utilisateur a la permission globale
            request.user.has_hierarchy_access = request.user.has_perm("APP_G2S.view_all")
        return self.get_response(request)




class PerformanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        queries = len(connection.queries)

        response.headers['X-Process-Time'] = f"{duration:.2f}s"
        response.headers['X-DB-Queries'] = queries
        return response



class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Récupérer le nom d'hôte de la requête
        hostname = request.get_host().split(':')[0]

        # Extraire le sous-domaine (tout ce qui précède le domaine principal)
        subdomain = hostname.split('.')[0]

        # Si nous sommes en mode développement local, gérer les cas spéciaux
        if settings.DEBUG and (hostname == 'localhost' or hostname == '127.0.0.1'):
            # En développement, utiliser un paramètre de requête pour simuler différents tenants
            tenant_id = request.GET.get('tenant_id')
            if tenant_id:
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                    request.tenant = tenant
                    return self.get_response(request)
                except Tenant.DoesNotExist:
                    pass
            # Priorité 2 : Session
            tenant_id = request.session.get('tenant_id')
            if tenant_id:
                try:
                    request.tenant = Tenant.objects.get(id=tenant_id)
                    return self.get_response(request)
                except Tenant.DoesNotExist:
                    pass

            # Si aucun tenant_id n'est spécifié ou s'il est invalide, utiliser le premier tenant actif
            try:
                tenant = Tenant.objects.filter(is_active=True).first()
                if tenant:
                    request.tenant = tenant
                    return self.get_response(request)
            except:
                pass
        else:
            # En production, rechercher le tenant par son sous-domaine
            try:
                tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
                request.tenant = tenant
                return self.get_response(request)
            except Tenant.DoesNotExist:
                # Si le sous-domaine ne correspond à aucun tenant, vérifier si c'est le domaine principal
                if hasattr(settings, 'MAIN_DOMAIN') and subdomain == settings.MAIN_DOMAIN:
                    # Le domaine principal peut accéder à l'interface d'administration multi-tenant
                    request.tenant = None
                    return self.get_response(request)

        # Si nous arrivons ici, aucun tenant valide n'a été trouvé
        if hasattr(settings, 'TENANT_REQUIRED') and settings.TENANT_REQUIRED:
            raise Http404("École non trouvée")

        # Si les tenants ne sont pas obligatoires, continuer sans tenant
        request.tenant = None
        return self.get_response(request)
