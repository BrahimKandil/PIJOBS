import os

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Candidature


ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": "form-control",
        "placeholder": "Nom d'utilisateur",
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control",
        "placeholder": "Mot de passe",
    }))


class CandidatureForm(forms.ModelForm):
    class Meta:
        model = Candidature
        fields = [
            "full_name",
            "email",
            "phone",
            "years_of_experience",
            "cover_message",
            "cv_file",
            "motivation_letter_file",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "years_of_experience": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "cover_message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "cv_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "motivation_letter_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_cv_file(self):
        file = self.cleaned_data.get("cv_file")
        if not file:
            raise forms.ValidationError("Le CV est obligatoire.")

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Format de CV non autorisé. Utilisez PDF, DOC ou DOCX.")

        if file.size > MAX_FILE_SIZE:
            raise forms.ValidationError("Le fichier CV dépasse 5 Mo.")

        return file

    def clean_motivation_letter_file(self):
        file = self.cleaned_data.get("motivation_letter_file")
        if not file:
            return file

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Format de lettre non autorisé. Utilisez PDF, DOC ou DOCX.")

        if file.size > MAX_FILE_SIZE:
            raise forms.ValidationError("Le fichier dépasse 5 Mo.")

        return file


class RejectionForm(forms.Form):
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Motif du refus"
        })
    )