from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import (
    User, RecruiterProfile, CandidateProfile,
    Candidature, RejectedCandidature,
)


# ----------------- formulaires existants -----------------
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Password'
    }))


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']


class RecruiterForm(forms.ModelForm):
    class Meta:
        model = RecruiterProfile
        fields = ['company_name', 'sector', 'phone', 'address']


class CandidateForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ['skills', 'experience', 'education', 'phone']


# ----------------- NOUVEAU : Candidature à une offre -----------------
ALLOWED_CV_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_CV_SIZE_MB = 5


class CandidatureForm(forms.ModelForm):
    """
    Formulaire rempli par le candidat pour postuler à une offre.
    Validation forte sur les fichiers (extension + taille).
    """

    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Nom et prénom'
        }),
        label="Nom complet",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'email@exemple.com'
        }),
        label="Email",
    )
    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': '+216 ...'
        }),
        label="Téléphone",
    )
    years_of_experience = forms.IntegerField(
        min_value=0, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Années d'expérience",
    )
    cover_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Message de motivation (court)",
    )
    cv_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control', 'accept': '.pdf,.doc,.docx'
        }),
        label="CV (PDF / DOC / DOCX)",
    )
    motivation_letter_file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control', 'accept': '.pdf,.doc,.docx'
        }),
        label="Lettre de motivation (fichier, optionnel)",
    )

    class Meta:
        model = Candidature
        fields = [
            "full_name", "email", "phone",
            "years_of_experience", "cover_message",
            "cv_file", "motivation_letter_file",
        ]

    # ---------- Validation des fichiers ----------
    def _validate_file(self, f, field_label):
        if not f:
            return
        name = getattr(f, "name", "") or ""
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED_CV_EXTENSIONS:
            raise ValidationError(
                f"{field_label} : extension non autorisée ({ext or 'aucune'})."
            )
        size = getattr(f, "size", 0) or 0
        if size > MAX_CV_SIZE_MB * 1024 * 1024:
            raise ValidationError(
                f"{field_label} : fichier trop volumineux (>{MAX_CV_SIZE_MB} Mo)."
            )

    def clean_cv_file(self):
        f = self.cleaned_data.get("cv_file")
        self._validate_file(f, "CV")
        return f

    def clean_motivation_letter_file(self):
        f = self.cleaned_data.get("motivation_letter_file")
        self._validate_file(f, "Lettre de motivation")
        return f


class RejectionForm(forms.Form):
    """Formulaire utilisé par le RH pour saisir un motif de refus."""
    reason = forms.CharField(
        required=False,
        max_length=2000,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Motif (optionnel)'
        }),
    )
