from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django import forms

from accounts.models import User, RecruitmentPost
import accounts
from .models import User, RecruiterProfile,CandidateProfile
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username'
    }))

    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
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


class RecruitmentPostForm(forms.ModelForm):
    class Meta:
        model = RecruitmentPost

        fields = [
            'title',
            'domain',
            'description',
            'max_candidatures',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'required_skills': forms.Textarea(attrs={'rows': 3}),
        }

from django import forms

from accounts.models import Candidature


class CandidatureForm(forms.ModelForm):

    custom_cv = forms.FileField(
        required=False
    )

    class Meta:

        model = Candidature

        fields = [
            "motivation_letter",
            "custom_cv"
        ]

        widgets = {
            "motivation_letter": forms.Textarea(
                attrs={
                    "rows": 5
                }
            )
        }