from django import forms
from django.core.exceptions import ValidationError
from django.db.models.aggregates import Sum
from django.urls import reverse_lazy
from phonenumber_field.formfields import PhoneNumberField

from APP_G2S.models import Eleve, BulletinPerformance, Periode, NoteExamen, Examen, Paiement, Enseignant, Note, Matiere, \
    Classe, EmploiDuTemps, Absence, PeriodePaiement, TranchePaiement, HistoriqueAcademique


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
        fields = ['nom', 'prenom', 'prenom_pere', 'nom_pere', 'prenom_mere', 'nom_mere', 'telephone', 'classe', 'age', 'profile_picture', 'residence']
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

        if not date:
            raise ValidationError("La date de début est obligatoire.")
        if not date_fin:
            raise ValidationError("La date de fin est obligatoire.")
        if not classe:
            raise ValidationError("Au moins une classe doit être sélectionnée.")

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
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        # Validation des dates
        if date_debut and date_fin and date_debut > date_fin:
            self.add_error('date_fin', "La date de fin doit être postérieure à la date de début")
            raise ValidationError("Incohérence temporelle")

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
        fields = '__all__'
        widgets = {
            'classe': forms.Select(attrs={
            'class': 'form-control form-select',
            'placeholder': 'Classe',
            'style': 'width: 100%;'
            }),
            'eleve': forms.Select(attrs={
            'class': 'form-control form-select',
            'placeholder': 'Élève',
            'style': 'width: 100%;'
            }),
            'motif': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Motif de l\'absence',
            'maxlength': '200',
            'style': 'resize:vertical; min-height:38px;'
            }),
            'justification_commentaire': forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Justification commentaire de l\'absence',
            'maxlength': '200',
            'rows': 2,
            'style': 'resize:vertical; min-height:38px;'
            }),
            'date': forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'placeholder': 'Date de l\'absence',
            'min': '2000-01-01',
            'max': '2100-12-31',
            'autocomplete': 'off'
            })
        }

        def __init__(self, *args, **kwargs):
            emplois = kwargs.pop('emplois', EmploiDuTemps.objects.all())
            eleves = kwargs.pop('eleves', Eleve.objects.all())
            super().__init__(*args, **kwargs)
            self.fields['emploi_du_temps'].queryset = emplois
            self.fields['eleve'].queryset = eleves



class PeriodePaiementForm(forms.ModelForm):
    classe = forms.ModelMultipleChoiceField(
        queryset=Classe.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    examen = forms.ModelChoiceField(
        queryset=Examen.objects.filter(validite='EN_COURS'),
        required=False,
        help_text="Examen associé (optionnel)"
    )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['periode'].queryset = PeriodePaiement.objects.filter(
            mode_paiement='PARTIEL'
        )

    class Meta:
        model = PeriodePaiement
        fields = [
            'nom', 'date_debut', 'date_fin', 'montant_total',
            'classe', 'examen', 'mode_paiement', 'nombre_tranches',
            'rappel_jours', 'modalites_paiement'
        ]
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'modalites_paiement': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'nombre_tranches': "Nombre d'échéances"
        }

    def clean_montant_total(self):
        montant = self.cleaned_data['montant_total']
        if montant < 5000:
            raise forms.ValidationError("Le montant minimum est de 5000 FCFA")
        return montant

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        examen = cleaned_data.get('examen')
        periode = cleaned_data.get('periode')
        eleve = cleaned_data.get('eleve')
        montant = cleaned_data.get('montant_paye')

        if date_debut and date_fin:
            if date_debut > date_fin:
                raise ValidationError("La date de fin doit être postérieure à la date de début")

            if examen:
                if date_debut < examen.date or date_fin > examen.date_fin:
                    raise ValidationError(
                        f"Les dates doivent être comprises entre {examen.date} et {examen.date_fin}"
                    )

        if periode and eleve and montant:
            tranche = periode.prochaine_tranche_eleve(eleve)
            if not tranche:
                raise ValidationError("Toutes les tranches sont déjà payées pour cette période")

            reste = tranche.montant - tranche.montant_paye_eleve(eleve)
            if montant > reste:
                raise ValidationError(
                    f"Montant maximum autorisé pour cette tranche : {reste} XOF"
                )

            cleaned_data['tranche'] = tranche

        return cleaned_data


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['periode', 'montant_paye', 'mode_paiement']
        widgets = {
            'periode': forms.Select(attrs={'class': 'form-control'}),
            'montant_paye': forms.NumberInput(attrs={'step': '500'}),
            'mode_paiement': forms.RadioSelect()
        }


class PaiementEspeceForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['eleve', 'periode', 'tranche', 'montant_paye']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Précharger les élèves avec leur classe pour l'affichage dans le template
        self.fields['eleve'].queryset = Eleve.objects.select_related('classe').all()

        self.fields['tranche'].queryset = TranchePaiement.objects.none()

        if 'periode' in self.data:
            try:
                periode_id = int(self.data.get('periode'))
                self.fields['tranche'].queryset = TranchePaiement.objects.filter(
                    periode_id=periode_id
                ).order_by('ordre')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['tranche'].queryset = self.instance.periode.tranchepaiement_set.all()

    def clean_montant_paye(self):
        montant = self.cleaned_data['montant_paye']
        periode = self.cleaned_data['periode']
        eleve = self.cleaned_data['eleve']
        tranche = self.cleaned_data.get('tranche')

        montant_restant = periode.montant_restant_eleve(eleve)

        if tranche:
            montant_tranche_restant = tranche.montant - tranche.paiement_set.filter(
                eleve=eleve
            ).aggregate(total=Sum('montant_paye'))['total'] or 0

            if montant > montant_tranche_restant:
                raise forms.ValidationError(
                    f"Le montant dépasse le reste dû pour cette tranche ({montant_tranche_restant} XOF)"
                )
        else:
            if montant > montant_restant:
                raise forms.ValidationError(
                    f"Le montant dépasse le reste dû ({montant_restant} XOF)"
                )

        return montant



class ValiderPaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = ['statut_paiement', 'commentaire']
        widgets = {
            'statut_paiement': forms.RadioSelect()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['statut_paiement'].choices = [
            ('REUSSI', 'Confirmer le paiement'),
            ('ANNULE', 'Annuler le paiement'),
            ('ECHOUE', 'Marquer comme échoué')
        ]

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
        return cleaned_data

class HistoriqueAcademiqueForm(forms.ModelForm):
    class Meta:
        model = HistoriqueAcademique
        fields = ['eleve', 'periode', 'moyenne', 'decision', 'paiement_complet']
        widgets = {
            'eleve': forms.Select(attrs={'class': 'form-select'}),
            'periode': forms.Select(attrs={'class': 'form-select'}),
            'moyenne': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 100}),
            'decision': forms.Select(attrs={'class': 'form-select'}),
            'paiement_complet': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Optionally, add custom validation here if needed
        return cleaned_data
