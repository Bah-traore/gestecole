from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from phonenumber_field.formfields import PhoneNumberField

from APP_G2S.models import Eleve, BulletinPerformance, Periode, NoteExamen, Examen, Paiement, Enseignant, Note, Matiere, \
    Classe, EmploiDuTemps, Absence, PeriodePaiement


class LoginAdminFrom(forms.Form):
    identifiant = forms.CharField(label="Identifiant administrateur")
    password = forms.CharField(widget=forms.PasswordInput)



class SMSVerificationForm(forms.Form):
    code = forms.CharField(label="Code de vérification SMS", max_length=6)

class LoginForm(forms.Form):
    telephone = PhoneNumberField(
        label="Numéro de téléphone",
        widget=forms.TextInput(attrs={'placeholder': '+223... ou 77...'}),
        region='ML'
    ) # forms.CharField(label="Numero Telephone", max_length=10, widget=forms.TextInput(attrs={'placeholder': '+223... ou 77...'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Mot de passe'}, render_value=False))

class EleveCreationForm(forms.ModelForm):
    class Meta:
        model = Eleve
        fields = ['nom', 'prenom', 'prenom_parent', 'nom_parent', 'telephone', 'classe', 'age', 'profile_picture', 'residence']
        widgets = {
            'telephone': forms.TextInput(attrs={'placeholder': '+223... ou 77...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classe'].required = True

    def clean_telephone(self):
        telephone = self.cleaned_data['telephone']
        if Eleve.objects.filter(telephone=telephone).exists():
            raise ValidationError("Ce numéro de téléphone est déjà utilisé")
        return telephone




class EnseignantCreationForm(forms.ModelForm):
    class Meta:
        model = Enseignant
        fields = [
            'telephone',
            'nom_complet',
            'profile_picture',
            'matieres'
        ]
        widgets = {
            'matieres': forms.CheckboxSelectMultiple
        }


class BulletinForm(forms.ModelForm):
    classes = forms.ModelChoiceField(
        queryset=Classe.objects.all(),
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-600 dark:bg-gray-800'
        }),
    )


    class Meta:
        model = BulletinPerformance
        fields = ['classes', 'eleve', 'appreciation']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Activer la validation stricte uniquement en mode final
        if self.data.get('eleve'):
            self.fields['appreciation'].required = True



    def clean_periode(self):
        periode = self.cleaned_data['periode']
        if periode.cloture:
            raise forms.ValidationError("Cette période est déjà clôturée")
        return periode

    def clean(self):
        cleaned_data = super().clean()
        eleve = cleaned_data.get('eleve')
        periode = cleaned_data.get('periode')
        classe = cleaned_data.get('classe')

        if eleve and classe and eleve.classe != classe:
            raise forms.ValidationError("L'élève ne fait pas partie de la classe sélectionnée.")

        if eleve and periode:
            if BulletinPerformance.objects.filter(eleve=eleve, periode=periode).exists():
                raise ValidationError("Un bulletin existe déjà pour cet élève et cette période.")
            if periode.cloture:
                raise ValidationError("Cette période est clôturée.")
        return cleaned_data

class NoteExamenForm(forms.ModelForm):
    class Meta:
        model = NoteExamen
        fields = ['examen', 'note', 'matiere']


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['valeur', 'periode', 'classe']


    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields['periode'].queryset = Periode.objects.filter(is_active=True)
    #



class ExamenForm(forms.ModelForm):
    class Meta:
        model = Examen
        fields = ['nom', 'date', 'date_fin', 'classe', 'periode', 'validite']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            # 'matieres': forms.CheckboxSelectMultiple(),
            'classe': forms.CheckboxSelectMultiple()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrage dynamique des périodes actives
        self.fields['periode'].queryset = Periode.objects.filter(
            is_active=True,
            cloture=False
        )

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        date_fin = cleaned_data.get('date_fin')
        classe = cleaned_data.get('classe')

        if date and date_fin and date > date_fin:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")

        if classe:
            for cl in classe:
                if Examen.objects.filter(date=date, classe__in=[cl]).exclude(id=self.instance.id).exists():
                    raise ValidationError(f"Un examen existe déjà pour la classe {cl} à cette date.")
        return cleaned_data

class PeriodeForm(forms.ModelForm):
    class Meta:
        model = Periode
        fields = ['numero', 'annee_scolaire', 'classe', 'date_debut', 'date_fin', 'is_active', 'cloture']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'classe': forms.CheckboxSelectMultiple()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classe'].queryset = Classe.objects.all().order_by('niveau')

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        date_fin = cleaned_data.get('date_fin')
        classe = cleaned_data.get('classe')

        # Validation des dates
        if date and date_fin and date > date_fin:
            self.add_error('date_fin', "La date de fin doit être postérieure à la date de début")
            raise ValidationError("Incohérence temporelle")

        # Validation de l'unicité
        if classe and date:
            if Examen.objects.filter(date=date, classe__in=[classe]).exists():
                self.add_error('date', "Un examen existe déjà pour cette date et classe")
        return cleaned_data

class MatiereForm(forms.ModelForm):
    class Meta:
        model = Matiere
        fields = ['nom', 'coefficient']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'coefficient': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'classe': forms.Select(attrs={'class': 'form-control'})
        }


    def clean_nom(self):
        nom = self.cleaned_data['nom'].upper()
        if self.Meta.model.objects.exclude(pk=self.instance.pk).filter(nom=nom).exists():
            raise forms.ValidationError("Cette matière existe déjà.")
        return nom


class ClasseForm(forms.ModelForm):

    class Meta:
        model = Classe
        fields = ['niveau', 'section', 'matieres']
        widgets = {
            'matieres': forms.CheckboxSelectMultiple
        }

        # def clean(self):
    #         cleaned_data = super().clean()
    #         niveau = cleaned_data.get('niveau')
    #         section = cleaned_data.get('section')
    #
    #         if niveau and section:
    #             if Classe.objects.filter(niveau=niveau, section=section).exists():
    #                 raise ValidationError("Cette classe existe déjà")
    #         return cleaned_data


    # SECTION_CHOICES = [
    #     ('A', 'Section A'),
    #     ('B', 'Section B'),
    #     ('C', 'Section C'),
    # ]
    #
    # section = forms.ChoiceField(
    #     choices=SECTION_CHOICES,
    #     widget=forms.Select(attrs={'class': 'form-control'})
    # )
    #
    # class Meta:
    #     model = Classe
    #     fields = ['niveau', 'section', 'responsable']
    #     widgets = {
    #         'niveau': forms.NumberInput(attrs={
    #             'class': 'form-control',
    #             'min': 1,
    #             'max': 12
    #         }),
    #         'responsable': forms.Select(attrs={'class': 'form-control'})
    #     }
    #
    #


class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = ['eleve', 'emploi_du_temps', 'justification_status', 'justification_document', 'motif']
        widgets = {
            'motif': forms.Textarea(attrs={'rows': 3}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les emplois du temps par classe de l'élève
        if 'eleve' in self.data:
            try:
                eleve_id = self.data.get('eleve')
                eleve = Eleve.objects.get(id=eleve_id)
                self.fields['emploi_du_temps'].queryset = EmploiDuTemps.objects.filter(classe=eleve.classe)
            except (ValueError, TypeError, Eleve.DoesNotExist):
                pass


class PeriodePaiementForm(forms.ModelForm):
    class Meta:
        model = PeriodePaiement
        fields = ['nom', 'classe', 'date_debut', 'date_fin', 'montant', 'examen']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
        }


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['periode', 'montant_paye', 'mode_paiement']
        widgets = {
            'periode': forms.Select(attrs={'class': 'form-control'}),
            'montant_paye': forms.NumberInput(attrs={'step': '500'}),
            'mode_paiement': forms.RadioSelect()
        }


class PaiementFormEspeces(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['eleve', 'periode', 'montant_paye']
        widgets = {
            'eleve': forms.Select(attrs={'class': 'form-control'}),
            'periode': forms.Select(attrs={'class': 'form-control'}),
            'montant_paye': forms.NumberInput(attrs={'class': 'form-control', 'step': '500'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['periode'].queryset = PeriodePaiement.objects.all()

class EmploiDuTempsForm(forms.ModelForm):
    class Meta:
        model = EmploiDuTemps
        fields = ['date', 'start_time', 'end_time', 'classe', 'matiere', 'recurrence', 'enseignant', 'salle']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    '''
    Au lieu de compte sur le form de django, on utilise l'authentification de django pour authentifier l'utilisateur.
   
        # if telephone and password:
        #
        #     user = authenticate(telephone=telephone, password=password)

        reduire le code au niveau de l'authentification user avec ces execeptions'

            # try:
            #     user = authenticate(telephone=telephone.as_e164, password=password)
            # except user.AttributeError:
            #     raise forms.ValidationError("Identifiants invalides.")
            # except user.UnboundLocalError:
        #     #     raise forms.ValidationError("Le Compte N'est pas rengistrer, Veuillez vous inscrire")
        #     if user is None:
        #         raise forms.ValidationError("Identifiants invalides.")
        #     cleaned_data['user'] = user
        # return cleaned_data
'''
class LoginFormAgent(forms.Form):
    matricule = forms.CharField(label="Matricule", max_length=20)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        type_vehicule = cleaned_data.get('type_vehicule')
        infraction = cleaned_data.get('infractions_listePv')

        if type_vehicule and infraction:
            if infraction.type_vehicule != type_vehicule:
                raise forms.ValidationError(
                    "Cette infraction n'est pas valide pour le type de véhicule sélectionné."
                )
        return cleaned_data



class PasswordResetRequestForm(forms.Form):
    telephone = PhoneNumberField(
        label="Numéro de téléphone enregistré",
        widget=forms.TextInput(attrs={'placeholder': '+223... ou 77...'}),
        region='ML'
    )

class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Nouveau mot de passe'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirmer le mot de passe'})
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('new_password') != cleaned_data.get('confirm_password'):
            raise ValidationError("Les mots de passe ne correspondent pas")
