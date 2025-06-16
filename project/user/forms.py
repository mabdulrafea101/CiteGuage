from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, ResearcherProfile, ResearchPaper
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users with email as the unique identifier."""
    
    email = forms.EmailField(
        label=_("Email address"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    first_name = forms.CharField(
        label=_("First name"),
        max_length=30,
        required=True
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=150,
        required=True
    )
    
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name in ['password1', 'password2']:
                field.widget.attrs['placeholder'] = '••••••••'
            elif field_name == 'email':
                field.widget.attrs['placeholder'] = 'name@example.com'



class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form that uses email as the username field"""
    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'id': 'id_username',
                'placeholder': 'name@example.com',
                'required': True,
            }
        )
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'id': 'id_password',
                'placeholder': 'Password',
                'required': True,
            }
        )
    )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name')


class ResearcherProfileForm(forms.ModelForm):
    class Meta:
        model = ResearcherProfile
        fields = [
            'first_name', 'last_name', 'institution', 'department', 'position', 
            'bio', 'profile_picture', 'research_interests', 'orcid_id', 
            'google_scholar_id', 'research_gate_url', 'website'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'research_interests': forms.TextInput(attrs={'class': 'form-control'}),
            'orcid_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0000-0000-0000-0000'}),
            'google_scholar_id': forms.TextInput(attrs={'class': 'form-control'}),
            'research_gate_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.researchgate.net/profile/...'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }



class ResearchPaperForm(forms.ModelForm):
    class Meta:
        model = ResearchPaper
        exclude = ('researcher', 'citation_count', 'predicted_citations', 'confidence_score')
        widgets = {
            'abstract': forms.Textarea(attrs={'rows': 5}),
            'publication_date': forms.DateInput(attrs={'type': 'date'}),
        }
