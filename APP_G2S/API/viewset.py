# from rest_framework.exceptions import ValidationError
#
# from gestecole.utils.services import MyLogin
# from rest_framework import viewsets, status, permissions
# from rest_framework.response import Response
# from rest_framework.decorators import action
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth import authenticate
# from django.utils import timezone
# from django.core.cache import cache
# from django.conf import settings
# from django_ratelimit.decorators import ratelimit
# from django.utils.decorators import method_decorator
# from APP_G2S.models import Citoyen, Agent, Contraventions
# from APP_G2S.API.serializers import (
#     CitoyenSerializers,
#     AgentSerializers,
#     ContraventionSerializers,
#     SMSVerificationSerializer,
#     ResendCodeSerializer
# )
# from APP_G2S.auth_backends import TelephoneBackend
# from gestecole.utils.securites import generate_secure_code
#     # send_secure_sms,
# #     TemporaryFileManager,
# #     secure_file_validation
# # )
# from django.db import transaction
# from gestecole.utils.file_handlers import save_files_to_temp, assign_files_to_user
#
# from rest_framework.permissions import BasePermission
#
# class IsCitoyenAuthenticated(BasePermission):
#     def has_permission(self, request, view):
#         return isinstance(request.user, Citoyen)
#
#
#
#
# ul = MyLogin()
#
#
# class SecureAuthViewSet(viewsets.ViewSet):
#     permission_classes = [permissions.AllowAny]
#
#     @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'))
#     @action(detail=False, methods=['post'], url_path='register')
#     def register(self, request):
#         serializer = CitoyenSerializers(data=request.data)
#         if serializer.is_valid():
#             try:
#                 # Génération de code sécurisé
#                 sms_code = generate_secure_code()
#                 expiration = timezone.now() + timezone.timedelta(minutes=10)
#
#                 # Stockage sécurisé dans le cache avec clé signée
#                 user_id = f"reg_{serializer.validated_data['telephone']}"
#                 saved_files = save_files_to_temp(request.FILES, user_id)
#                 cache.set(user_id, {
#                     'code': sms_code,
#                     'data': request.data,
#                     'files': saved_files,
#                     'expires': expiration
#                 }, 600)
#
#                 # Envoi sécurisé du SMS
#                 #send_secure_sms(serializer.validated_data['telephone'], sms_code)
#                 print(f"[CACHE] Stockage : {user_id} = {sms_code}")
#                 return Response({
#                     'status': 'Code de vérification envoyé',
#                     'expires_in': 600
#                 }, status=status.HTTP_202_ACCEPTED)
#
#             except Exception as e:
#                 return Response({
#                     'error': 'Erreur serveur',
#                     'code': 'SERVER_ERROR'
#                 }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#     @method_decorator(ratelimit(key='ip', rate='3/m', method='POST'))
#     @action(detail=False, methods=['post'], url_path='verify_sms')
#     def verify_sms(self, request):
#         serializer = SMSVerificationSerializer(data=request.data)
#         if serializer.is_valid():
#             telephone = serializer.validated_data['telephone']
#             code = serializer.validated_data['code']
#
#             cache_key = f"reg_{telephone}"
#             cached_data = cache.get(cache_key)
#             print(f"[CACHE] Récupération : {cache_key} -> {cached_data}")
#
#             if not cached_data:
#                 return Response(
#                     {"error": "Aucun code associé à ce numéro. Réinscrivez-vous."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#
#             # if not cached_data or cached_data['code'] != str(code):
#             #     return Response({
#             #         'error': 'Code invalide ou expiré',
#             #         'code': 'INVALID_CODE'
#             #     }, status=status.HTTP_400_BAD_REQUEST)
#
#             try:
#                 # Création sécurisée de l'utilisateur
#                 # if cached_data['data']['profile_image']
#                 with transaction.atomic():
#                     user = Citoyen.objects.create_user(
#                         username=cached_data['data']['first_name'] + "-" + cached_data['data']['last_name'],
#                         telephone=cached_data['data']['telephone'],
#                         password=cached_data['data']['password1'],
#                         first_name=cached_data['data']['first_name'],
#                         last_name=cached_data['data']['last_name'],
#                         profile_picture=  cached_data['data']['profile_image'] if not {} else cached_data['data']['profile_image']
#                     )
#
#                     refresh = RefreshToken.for_user(user)
#                     access_token = str(refresh.access_token)
#                     refresh_token = str(refresh)
#
#                     print("verification de l'eixstance des token", access_token, refresh_token)
#
#
#                     # Récupération des fichiers temporaires et assignation sécurisée
#                     temp_files = cached_data['files']
#                     if not assign_files_to_user(user, temp_files):
#                         raise ValidationError("Échec de l'assignation des fichiers")
#
#                 cache.delete(cache_key)
#                 return Response({
#                     'access': access_token,
#                     'refresh': refresh_token,
#                     'user': CitoyenSerializers(user).data
#                 }, status=status.HTTP_201_CREATED)
#
#             except Exception as e:
#                 return Response({
#                     'error': 'Erreur de création de compte',
#                     'code': 'ACCOUNT_CREATION_FAILED'
#                 }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#     @method_decorator(ratelimit(key='ip', rate='3/m', method='POST'))
#     @action(detail=False, methods=['post'], url_path='resend_code')
#     def resend_code(self, request):
#         serializer = ResendCodeSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#         telephone = serializer.validated_data['telephone']
#         cache_key = f"reg_{telephone}"
#         cached_data = cache.get(cache_key)
#
#         if not cached_data:
#             return Response(
#                 {"error": "Aucune demande de code active. Veuillez vous réinscrire."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         try:
#             # Generate new code and update cache
#             new_code = generate_secure_code()
#             expiration = timezone.now() + timezone.timedelta(minutes=10)
#
#             # Update cached data
#             cached_data['code'] = new_code
#             cached_data['expires'] = expiration
#             cache.set(cache_key, cached_data, 600)  # 10 minutes TTL
#
#             # Simulate SMS sending (uncomment send_secure_sms in production)
#             # send_secure_sms(telephone, new_code)
#             print(f"[CACHE] Code renvoyé : {cache_key} = {new_code}")
#
#             return Response({
#                 'status': 'Nouveau code envoyé',
#                 'expires_in': 600
#             }, status=status.HTTP_200_OK)
#
#         except Exception as e:
#             return Response({
#                 'error': 'Erreur serveur',
#                 'code': 'SERVER_ERROR'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#     @method_decorator(ratelimit(key='ip', rate='2/m', method='POST'))
#     @action(detail=False, methods=['post'], url_path='login')
#     def login(self, request):
#         telephone = request.data.get('telephone')
#         password = request.data.get('password')
#         # backend = TelephoneBackend()
#         user = authenticate(request, telephone=telephone, password=password)
#         if user and isinstance(user, Citoyen):
#             return self._create_secure_token_response(user)
#
#         return Response({
#             'error': 'Identifiants invalides',
#             'code': 'INVALID_CREDENTIALS'
#         }, status=status.HTTP_401_UNAUTHORIZED)
#
#     def _create_secure_token_response(self, user):
#         refresh = RefreshToken.for_user(user)
#         refresh['user_type'] = user.user_type
#         refresh['ip'] = self.request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
#         refresh.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])
#         print("_create_secure_token_response", str(refresh.access_token))
#         return Response({
#             'access': str(refresh.access_token),
#             'refresh': str(refresh),
#             'user': CitoyenSerializers(user).data
#         }, status=status.HTTP_200_OK)
#
#
# class ContraventionViewSet(viewsets.ModelViewSet):
#     serializer_class = ContraventionSerializers
#     permission_classes = [IsCitoyenAuthenticated]
#
#     def get_queryset(self):
#         user = self.request.user
#         if isinstance(user, Citoyen):
#             return Contraventions.objects.filter(telephone=user.telephone)
#         return Contraventions.objects.none()