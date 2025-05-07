from django.http import HttpResponse
from django.shortcuts import redirect, render
from functools import wraps
from django.http import HttpResponseForbidden

from APP_G2S.middleware import HierarchyMiddleware


def administrateur_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("connexion_admin")
        if hasattr(request.user, 'is_admin') and request.user.is_admin and request.user.role == 'DIRECTEUR' and HierarchyMiddleware.__call__:
            print(HierarchyMiddleware.__call__)
            return view_func(request, *args, **kwargs)
        return render(request, 'app_gouv_user/forbidden/messages_forbidden.html')
    return wrapper

def citoyen_required(view_func):
    def wrapper(request, *args, **kwargs):
        print(request.user.is_authenticated)
        if not request.user.is_authenticated:
            return redirect("login")  # {settings.LOGIN_URL}?next={request.path}
        try:
            print(request.user.is_authenticated)
            if request.user.is_eleve:
                print(request.user.is_authenticated)

                return view_func(request, *args, **kwargs)
        except AttributeError:
            return HttpResponse("ERROR!!!")
    return wrapper

def agent_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login_agent")  # {settings.LOGIN_URL}?next={request.path}
        try:
            if request.user.is_agent:
                return view_func(request, *args, **kwargs)
        except AttributeError:
            return render(request, 'app_gouv_user/forbidden/messages_forbidden.html')
    return wrapper



def role_required(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Accès non autorisé")
        return _wrapped_view
    return decorator

directeur_required = role_required('DIRECTEUR')
censeur_required = role_required('CENSEUR')
comptable_required = role_required('COMPTABLE')


def complex_permission(perm_codename, role=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Vérifier la hiérarchie
            if request.user.has_hierarchy_access:
                return view_func(request, *args, **kwargs)

            # Vérifier le groupe
            if role and request.user.role != role:
                return HttpResponseForbidden()

            # Vérifier la permission spécifique
            if not request.user.has_perm(perm_codename):
                return HttpResponseForbidden()

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
