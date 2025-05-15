from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from APP_G2S.models import Tenant
from .forms import TenantForm

def is_superadmin(user):
    return user.is_superuser or getattr(user, 'is_superadmin', False)

@user_passes_test(is_superadmin)
def dashboard(request):
    return render(request, "core_admin/dashboard.html")

@user_passes_test(is_superadmin)
def tenants_list(request):
    tenants = Tenant.objects.all()
    return render(request, "core_admin/tenants_list.html", {"tenants": tenants})

@user_passes_test(is_superadmin)
def tenant_create(request):
    if request.method == "POST":
        form = TenantForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                tenant = form.save(commit=False)
                tenant.save()
                form.save_m2m()
                messages.success(request, "École créée avec succès.")
                return redirect("core_admin:tenants_list")
            except Exception as e:
                messages.error(request, f"Erreur lors de la création : {e}")
        else:
            messages.error(request, "Formulaire invalide. Veuillez corriger les erreurs.")
    else:
        form = TenantForm()
    return render(request, "core_admin/tenant_form.html", {"form": form})

@user_passes_test(is_superadmin)
def tenant_edit(request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if request.method == "POST":
        form = TenantForm(request.POST, request.FILES, instance=tenant)
        if form.is_valid():
            try:
                tenant = form.save(commit=False)
                tenant.save()
                form.save_m2m()
                messages.success(request, "École modifiée avec succès.")
                return redirect("core_admin:tenants_list")
            except Exception as e:
                messages.error(request, f"Erreur lors de la modification : {e}")
        else:
            messages.error(request, "Formulaire invalide. Veuillez corriger les erreurs.")
    else:
        form = TenantForm(instance=tenant)
    return render(request, "core_admin/tenant_form.html", {"form": form})

@user_passes_test(is_superadmin)
def tenant_delete(request, tenant_id):
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if request.method == "POST":
        try:
            tenant.delete()
            messages.success(request, "École supprimée avec succès.")
            return redirect("core_admin:tenants_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression : {e}")
    return render(request, "core_admin/tenant_confirm_delete.html", {"tenant": tenant})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Déconnexion réussie.")
    return redirect("core_admin:login") 



from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    if request.user.is_authenticated and is_superadmin(request.user):
        return redirect('core_admin:dashboard')
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if is_superadmin(user):
                login(request, user)
                return redirect('core_admin:dashboard')
            else:
                messages.error(request, "Vous n'avez pas accès à cette interface.")
        else:
            messages.error(request, "Identifiants invalides.")
    else:
        form = AuthenticationForm()
    return render(request, "core_admin/login.html", {"form": form})