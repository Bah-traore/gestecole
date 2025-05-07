from datetime import timedelta
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from ratelimit.decorators import ratelimit
from app_gouv.forms import PasswordResetRequestForm, SetNewPasswordForm
from app_gouv.models import Citoyen

from django.conf import settings
from django.core.cache import cache

@ratelimit(key='post:telephone', rate='5/h', method='POST')
@csrf_protect
def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            telephone = form.cleaned_data['telephone']
            try:
                citoyen = Citoyen.objects.get(telephone=telephone)
                code = citoyen.generate_sms_code()
                print(code)
                request.session['reset_telephone'] = str(telephone)
                request.session['reset_code'] = code
                request.session['reset_code_expiry'] = str(timezone.now() + timedelta(minutes=15))
                # Envoyer le SMS réel ici (décommenter la partie SMS dans generate_sms_code)
                messages.success(request, "Un code de vérification a été envoyé par SMS")
                return redirect('password_reset_verify')
            except Citoyen.DoesNotExist:
                messages.error(request, "Aucun compte associé à ce numéro")
    else:
        form = PasswordResetRequestForm()
    return render(request, 'app_gouv_user/citoyen/reset_password/password_reset.html', {'form': form})


@csrf_protect
def password_reset_verify(request):
    if 'reset_telephone' not in request.session:
        return redirect('password_reset_request')

    if request.method == 'POST':
        code = request.POST.get('code', '')
        stored_code = request.session.get('reset_code', '')
        expiry = timezone.datetime.fromisoformat(request.session.get('reset_code_expiry', timezone.now()))
        print(stored_code)
        if timezone.now() > expiry:
            messages.error(request, "Le code a expiré")
            return redirect('password_reset_request')

        if code == stored_code:
            request.session['reset_verified'] = True
            return redirect('password_reset_confirm')
        else:
            messages.error(request, "Code invalide")

    return render(request, 'app_gouv_user/citoyen/reset_password/password_verify.html')


@csrf_protect
def password_reset_confirm(request):
    if not request.session.get('reset_verified'):
        return redirect('password_reset_request')

    if request.method == 'POST':
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            telephone = request.session['reset_telephone']
            citoyen = Citoyen.objects.get(telephone=telephone)
            citoyen.set_password(form.cleaned_data['new_password'])
            citoyen.save()

            keys = ['reset_telephone', 'reset_code', 'reset_code_expiry', 'reset_verified']
            [request.session.pop(k, None) for k in keys]

            messages.success(request, "Mot de passe réinitialisé avec succès !")
            return redirect('login')
    else:
        form = SetNewPasswordForm()

    return render(request, 'app_gouv_user/citoyen/reset_password/password_confirm.html', {'form': form})
