from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from functools import wraps
from django.http import HttpResponseForbidden
from django.urls import reverse
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User

from APP_G2S.middleware import HierarchyMiddleware
from APP_G2S.models import ApprovalRequest, AccessLog


def get_compatible_user(user):
    """
    Fonction auxiliaire pour obtenir les informations d'un utilisateur pour le modèle AccessLog.
    Retourne un dictionnaire avec custom_user_id et custom_user_type pour être utilisé avec le modèle AccessLog modifié.
    """
    if user and hasattr(user, 'id'):
        return {
            'custom_user_id': user.id,
            'custom_user_type': user.__class__.__name__
        }
    return {'custom_user_id': None, 'custom_user_type': None}


def administrateur_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("connexion_admin")
        if hasattr(request.user, 'is_admin') and request.user.is_admin and HierarchyMiddleware.__call__:
            return view_func(request, *args, **kwargs)
        return render(request, 'APP_G2S/forbidden/messages_forbidden.html')
    return wrapper


def role_required(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            print(group_names)
            print(request.user.groups.all())

            # Vérifier chaque rôle un par un
            for group_name in group_names:
                if request.user.groups.filter(name=group_name).exists():
                    return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("Accès non autorisé")
        return _wrapped_view
    return decorator

def multi_role_required(*decorators):
    """
    Décorateur qui combine plusieurs décorateurs role_required.
    Il vérifie chaque rôle un par un et permet l'accès si l'utilisateur possède l'un des rôles.

    Utilisation:
    @multi_role_required(directeur_required, censeur_required, surveillant_required)
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("connexion_admin")

            # Extraire les noms de rôles directement à partir des noms des décorateurs
            roles = []
            for decorator in decorators:
                if hasattr(decorator, '__closure__') and decorator.__closure__:
                    for cell in decorator.__closure__:
                        # Handle tuple case to extract string without parentheses
                        if isinstance(cell.cell_contents, tuple) and len(cell.cell_contents) == 1 and isinstance(cell.cell_contents[0], str):
                            print(cell.cell_contents[0])  # Print just the string value
                        else:
                            print(cell.cell_contents)
                        if hasattr(cell.cell_contents, '__name__'):
                            print(cell.cell_contents)
                        # Get the actual role name, handling tuple case
                        role_name = cell.cell_contents[0] if isinstance(cell.cell_contents, tuple) and len(cell.cell_contents) == 1 else cell.cell_contents
                        print(request.user.groups.all())
                        if request.user.groups.filter(name=role_name).first():
                            if hasattr(decorator, '__name__'):
                                    roles.append(role_name)


            # Vérifier chaque rôle un par un
            for role in roles:
                if request.user.groups.filter(name=role).exists():
                    return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("Accès non autorisé")
        return _wrapped_view
    return decorator

directeur_required = role_required('DIRECTEUR')
censeur_required = role_required('CENSEUR')
comptable_required = role_required('COMPTABLE')
surveillant_required = role_required('SURVEILLANT')


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

def directeur_only(view_func):
    """
    Décorateur qui restreint l'accès à une vue aux utilisateurs ayant le rôle DIRECTEUR uniquement.
    Les autres utilisateurs recevront une erreur 403 Forbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("connexion_admin")

        if request.user.role != 'DIRECTEUR':
            # Enregistrer la tentative d'accès non autorisée
            try:
                user_info = get_compatible_user(request.user)
                AccessLog.objects.create(
                    user=None,
                    custom_user_id=user_info['custom_user_id'],
                    custom_user_type=user_info['custom_user_type'],
                    action="UNAUTHORIZED_ACCESS",
                    url=request.get_full_path(),
                    details={"view": view_func.__name__},
                    status="denied"
                )
            except ValueError as e:
                # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
                error_message = str(e)
                return redirect(f"/erreur-user-type/?message={error_message}")
            except Exception as e:
                # Pour les autres erreurs, les logger mais continuer
                print(f"Directeur Erreur lors de la création du log d'accès: {e}")

            return render(request, 'APP_G2S/forbidden/messages_forbidden.html', {
                'message': 'Seul le directeur peut accéder à cette fonctionnalité.'
            })

        # Enregistrer l'accès autorisé
        try:
            user_info = get_compatible_user(request.user)
            print(user_info)
            print(user_info['custom_user_id'])
            AccessLog.objects.create(
                user=None,
                custom_user_id=user_info['custom_user_id'],
                custom_user_type=user_info['custom_user_type'],
                action="AUTHORIZED_ACCESS",
                url=request.get_full_path(),
                details={"view": view_func.__name__},
                status="success"
            )
        except ValueError as e:
            # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
            error_message = str(e)
            return redirect(f"/erreur-user-type/?message={error_message}")
        except Exception as e:
            # Pour les autres erreurs, les logger mais continuer
            print(f"directeur Erreur lors de la création du log d'accès: {e}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def censeur_only(view_func):
    """
    Décorateur qui restreint l'accès à une vue aux utilisateurs ayant le rôle CENSEUR ou DIRECTEUR.
    Les autres utilisateurs recevront une erreur 403 Forbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("connexion_admin")

        # Permettre l'accès aux directeurs et aux censeurs
        if request.user.role != 'CENSEUR' and request.user.role != 'DIRECTEUR':
            # Enregistrer la tentative d'accès non autorisée
            try:
                user_info = get_compatible_user(request.user)
                AccessLog.objects.create(
                    user=None,
                    custom_user_id=user_info['custom_user_id'],
                    custom_user_type=user_info['custom_user_type'],
                    action="UNAUTHORIZED_ACCESS",
                    url=request.get_full_path(),
                    details={"view": view_func.__name__},
                    status="denied"
                )
            except ValueError as e:
                # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
                error_message = str(e)
                return redirect(f"/erreur-user-type/?message={error_message}")
            except Exception as e:
                # Pour les autres erreurs, les logger mais continuer
                print(f"Censeur Erreur lors de la création du log d'accès: {e}")

            return render(request, 'APP_G2S/forbidden/messages_forbidden.html', {
                'message': 'Seul le censeur ou le directeur peut accéder à cette fonctionnalité.'
            })

        # Enregistrer l'accès autorisé
        try:
            user_info = get_compatible_user(request.user)
            AccessLog.objects.create(
                user=None,
                custom_user_id=user_info['custom_user_id'],
                custom_user_type=user_info['custom_user_type'],
                action="AUTHORIZED_ACCESS",
                url=request.get_full_path(),
                details={"view": view_func.__name__},
                status="success"
            )
        except ValueError as e:
            # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
            error_message = str(e)
            return redirect(f"/erreur-user-type/?message={error_message}")
        except Exception as e:
            # Pour les autres erreurs, les logger mais continuer
            print(f"censeur Erreur lors de la création du log d'accès: {e}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def comptable_only(view_func):
    """
    Décorateur qui restreint l'accès à une vue aux utilisateurs ayant le rôle COMPTABLE ou DIRECTEUR.
    Les censeurs n'ont pas accès à ces fonctionnalités.
    Les autres utilisateurs recevront une erreur 403 Forbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("connexion_admin")

        # Permettre l'accès aux directeurs et aux comptables, mais pas aux censeurs
        print(request.user.role)
        if request.user.role != 'COMPTABLE' and request.user.role != 'DIRECTEUR':
            # Enregistrer la tentative d'accès non autorisée
            try:
                user_info = get_compatible_user(request.user)
                print(user_info, 'dans le def comptable_only')
                print(user_info['custom_user_id'], 'dans le def comptable_only')
                print(user_info['custom_user_type'], 'dans le def comptable_only')
                AccessLog.objects.create(
                    user=None,
                    custom_user_id=user_info['custom_user_id'],
                    custom_user_type=user_info['custom_user_type'],
                    action="UNAUTHORIZED_ACCESS",
                    url=request.get_full_path(),
                    details={"view": view_func.__name__},
                    status="denied"
                )
            except ValueError as e:
                # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
                error_message = str(e)
                return redirect(f"/erreur-user-type/?message={error_message}")
            except Exception as e:
                # Pour les autres erreurs, les logger mais continuer
                print(f"comptable 1 Erreur lors de la création du log d'accès: {e}")

            return render(request, 'APP_G2S/forbidden/messages_forbidden.html', {
                'message': 'Seul le comptable ou le directeur peut accéder à cette fonctionnalité.'
            })

        # Enregistrer l'accès autorisé
        try:
            user_info = get_compatible_user(request.user)
            AccessLog.objects.create(
                user=None,
                custom_user_id=user_info['custom_user_id'],
                custom_user_type=user_info['custom_user_type'],
                action="AUTHORIZED_ACCESS",
                url=request.get_full_path(),
                details={"view": view_func.__name__},
                status="success"
            )
        except ValueError as e:
            # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
            error_message = str(e)
            return redirect(f"/erreur-user-type/?message={error_message}")
        except Exception as e:
            # Pour les autres erreurs, les logger mais continuer
            print(f"comptable 2 Erreur lors de la création du log d'accès: {e}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def surveillant_only(view_func):
    """
    Décorateur qui restreint l'accès à une vue aux utilisateurs ayant le rôle SURVEILLANT uniquement.
    Les autres utilisateurs recevront une erreur 403 Forbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("connexion_admin")

        if request.user.role != 'SURVEILLANT':
            # Enregistrer la tentative d'accès non autorisée
            try:
                user_info = get_compatible_user(request.user)
                AccessLog.objects.create(
                    user=None,
                    custom_user_id=user_info['custom_user_id'],
                    custom_user_type=user_info['custom_user_type'],
                    action="UNAUTHORIZED_ACCESS",
                    url=request.get_full_path(),
                    details={"view": view_func.__name__},
                    status="denied"
                )
            except ValueError as e:
                # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
                error_message = str(e)
                return redirect(f"/erreur-user-type/?message={error_message}")
            except Exception as e:
                # Pour les autres erreurs, les logger mais continuer
                print(f"surveillant 1 Erreur lors de la création du log d'accès: {e}")

            return render(request, 'APP_G2S/forbidden/messages_forbidden.html', {
                'message': 'Seul le surveillant peut accéder à cette fonctionnalité.'
            })

        # Enregistrer l'accès autorisé
        try:
            user_info = get_compatible_user(request.user)
            AccessLog.objects.create(
                user=None,
                custom_user_id=user_info['custom_user_id'],
                custom_user_type=user_info['custom_user_type'],
                action="AUTHORIZED_ACCESS",
                url=request.get_full_path(),
                details={"view": view_func.__name__},
                status="success"
            )
        except ValueError as e:
            # Si une erreur de type d'utilisateur se produit, rediriger vers la page d'erreur
            error_message = str(e)
            return redirect(f"/erreur-user-type/?message={error_message}")
        except Exception as e:
            # Pour les autres erreurs, les logger mais continuer
            print(f"surveillant 2 Erreur lors de la création du log d'accès: {e}")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def requires_approval(action_type, model=None, id_param=None):
    """
    Décorateur qui permet aux directeurs d'accéder directement à une vue,
    mais qui crée une demande d'approbation pour les autres rôles.

    Les directeurs peuvent modifier n'importe quel objet, peu importe son âge.

    Après 24 heures, le censeur ne peut pas modifier ou supprimer sans l'approbation du directeur.

    Args:
        action_type: Le type d'action qui nécessite une approbation
        model: Le modèle de l'objet à vérifier (pour la règle des 24h)
               Peut être un modèle unique ou une liste/tuple de modèles
        id_param: Le nom du paramètre contenant l'ID de l'objet
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("connexion_admin")

            # Vérifier si l'objet existe et a été créé il y a plus de 24h
            needs_approval = False
            object_info = {}

            if model and id_param and id_param in kwargs:
                try:
                    obj_id = kwargs[id_param]

                    # Vérifier si model est une liste ou un tuple
                    if isinstance(model, (list, tuple)):
                        models_list = model
                    else:
                        models_list = [model]

                    # Parcourir tous les modèles
                    for current_model in models_list:
                        try:
                            obj = get_object_or_404(current_model, pk=obj_id)

                            # Vérifier si l'objet a été créé il y a plus de 24h
                            if hasattr(obj, 'created_at'):
                                creation_time = obj.created_at
                            elif hasattr(obj, 'date_creation'):
                                creation_time = obj.date_creation
                            elif hasattr(obj, 'date'):
                                creation_time = obj.date
                            else:
                                # Si on ne peut pas déterminer la date de création, on suppose que c'est ancien
                                creation_time = timezone.now() - timedelta(days=2)

                            # Si l'objet a été créé il y a plus de 24h, il faut une approbation
                            if timezone.now() - timedelta(hours=24) > creation_time:
                                needs_approval = True
                                object_info = {
                                    'id': obj_id,
                                    'model': current_model.__name__,
                                    'creation_date': str(creation_time)
                                }
                                # Si on a trouvé un objet qui nécessite une approbation, on peut arrêter la recherche
                                break
                        except Exception as e:
                            # Si on ne trouve pas l'objet avec ce modèle, on continue avec le suivant
                            continue
                except Exception as e:
                    # En cas d'erreur générale, on continue sans vérifier la date
                    print("ERREUR BUG EXCEPTION @REQUIRES_APPROVAL", str(e))
                    pass

            # Les directeurs peuvent accéder directement, peu importe l'âge de l'objet
            if request.user.role == 'DIRECTEUR':
                return view_func(request, *args, **kwargs)

            # Si c'est un censeur qui veut créer un examen, on le laisse faire
            if action_type == 'creer_examen' and request.user.role == 'CENSEUR' and request.method == 'POST':
                return view_func(request, *args, **kwargs)

            # Si c'est un censeur et que l'objet a moins de 24h, on le laisse modifier/supprimer
            if request.user.role == 'CENSEUR' and not needs_approval and request.method == 'POST':
                # Pour les actions de modification ou suppression
                if action_type.startswith('modifier_') or action_type.startswith('supprimer_'):
                    return view_func(request, *args, **kwargs)

            # Pour les autres rôles ou si l'objet a plus de 24h, créer une demande d'approbation
            if request.method == 'POST' and request.user.role != 'DIRECTEUR':
                # Extraire les données pertinentes de la requête
                target_data = {
                    'post_data': dict(request.POST),
                    'view': view_func.__name__,
                    'url': request.get_full_path(),
                    'object_info': object_info
                }

                # Créer la demande d'approbation
                ApprovalRequest.create_request(
                    requester=get_compatible_user(request.user),
                    action_type=action_type,
                    target_object=target_data,
                    action_metadata={
                        'args': args,
                        'kwargs': kwargs
                    }
                )

                if request.user.role == 'DIRECTEUR':
                    # Les directeurs ne devraient jamais arriver ici, mais au cas où
                    messages.info(request, 
                        "Votre action a été traitée directement sans nécessiter d'approbation.")
                elif request.user.role == 'CENSEUR' and needs_approval and (action_type.startswith('modifier_') or action_type.startswith('supprimer_')):
                    messages.info(request, 
                        "Cet objet a été créé il y a plus de 24 heures. Votre demande de modification/suppression a été soumise et est en attente d'approbation par le directeur.")
                else:
                    messages.info(request, 
                        "Votre demande a été soumise et est en attente d'approbation par le directeur.")
                return redirect(request.META.get('HTTP_REFERER', '/'))

            # Si c'est juste une requête GET, afficher un message d'avertissement
            if needs_approval:
                if request.user.role == 'DIRECTEUR':
                    # Pas de message d'avertissement pour les directeurs
                    pass
                elif request.user.role == 'CENSEUR' and (action_type.startswith('modifier_') or action_type.startswith('supprimer_')):
                    messages.warning(request, 
                        "Cet objet a été créé il y a plus de 24 heures. En tant que censeur, vous ne pouvez pas le modifier ou le supprimer sans l'approbation du directeur.")
                else:
                    messages.warning(request, 
                        "Cet objet a été créé il y a plus de 24 heures. Toute modification nécessite l'approbation du directeur.")
            elif request.user.role != 'DIRECTEUR':
                messages.warning(request, 
                    "Cette action nécessite l'approbation du directeur.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator

def tenant_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from gestecole.utils.tenant import get_current_tenant
        tenant = get_current_tenant()
        if not tenant:
            return render(request, 'APP_G2S/forbidden/messages_forbidden.html', {
                'message': 'Aucun tenant sélectionné. Veuillez réessayer.'
            })
        request.tenant = tenant
        return view_func(request, *args, **kwargs)
    return _wrapped_view
