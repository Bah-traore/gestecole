from APP_G2S.models import Citoyen, Agent, Administrateur, Contraventions
from rest_framework import serializers
from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumber_field.serializerfields import PhoneNumberField




class CitoyenSerializers(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Citoyen
        fields = ['id', 'telephone', 'first_name', 'last_name']
        extra_kwargs ={'password': {'write_only': True}}

    # def validate_phone(self, telephone):
    #     parsed = parse(telephone, "ML")
    #     return format_number(parsed, PhoneNumberFormat.E164)

class AgentSerializers(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Agent
        fields  = ['id', 'matricule', 'telephone', 'prenom', 'nom', 'is_agent', 'password']
        extra_kwargs ={'password': {'write_only': True}}


class ContraventionSerializers(serializers.ModelSerializer):
    class Meta:
        model = Contraventions
        fields = '__all__' # ['id', 'telephone', 'infractions_listePv', 'nom', 'agent', 'type_vehicule', 'info_vehicule', 'lieu', 'date', 'status']
        extra_kwargs ={'password': {'write_only': True}}



class SMSVerificationSerializer(serializers.Serializer):
    telephone = PhoneNumberField(
        label=_("Numéro de téléphone"),
        help_text=_("Format international: +223........"),
        region="ML",
        required=True
    )
    code = serializers.CharField(
        label=_("Code de vérification"),
        max_length=6,
        min_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message=_("Le code doit être composé de 6 chiffres")
            )
        ],
        required=True
    )

    def validate_telephone(self, value):
        """Validation supplémentaire du numéro"""
        if not value.is_valid():
            raise serializers.ValidationError(_("Numéro de téléphone invalide"))
        return value.as_e164

    def validate(self, attrs):
        """Validation croisée"""
        telephone = attrs.get('telephone')
        code = attrs.get('code')

        # Vérification de cohérence (optionnel)
        if telephone and code:
            # Ici on pourrait ajouter des vérifications de format avancées
            pass

        return attrs

class ResendCodeSerializer(serializers.Serializer):
    telephone = serializers.CharField(required=True, max_length=20)