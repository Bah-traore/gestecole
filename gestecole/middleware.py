from django.utils.deprecation import MiddlewareMixin
from APP_G2S.models import Tenant
from gestecole.utils.tenant import set_current_tenant

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0] if '.' in host else None
        tenant = None
        if subdomain and subdomain not in ['www', 'localhost']:
            try:
                tenant = Tenant.objects.get(subdomain=subdomain)
            except Tenant.DoesNotExist:
                tenant = None
        set_current_tenant(tenant)
        request.tenant = tenant
