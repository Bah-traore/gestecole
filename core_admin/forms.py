from django import forms
from APP_G2S.models import Tenant

class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        exclude = ['config']
