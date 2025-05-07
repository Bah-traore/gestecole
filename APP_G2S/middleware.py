# from django.http import Http404
# from APP_G2S.models import Tenant
#

class HierarchyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Vérifie si l'utilisateur a la permission globale
            request.user.has_hierarchy_access = request.user.has_perm("APP_G2S.view_all")
        return self.get_response(request)


import time
from django.db import connection


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



#
# class TenantMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response
#
#     def __call__(self, request):
#         host = request.get_host().split(':')[0]
#         subdomain = host.split('.')[0]
#
#         try:
#             request.tenant = Tenant.objects.get(subdomain=subdomain)
#         except Tenant.DoesNotExist:
#             raise Http404("Établissement non trouvé")
#
#         return self.get_response(request)


