from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django import forms

from accounts.models import User
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