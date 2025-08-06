from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, ResearcherProfile, Paper
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


class PaperForm(forms.ModelForm):
    # Add a custom field for authors if you want to capture them for display,
    # even if not used directly in prediction.
    # If you only rely on WoS for authors, you might not need this.
    authors = forms.CharField(
        max_length=1000,
        required=False, # Authors might be extracted from PDF or WoS
        help_text="Comma-separated list of author names (e.g., John Doe, Jane Smith)",
        widget=forms.TextInput(attrs={'placeholder': 'e.g., John Doe, Jane Smith'})
    )

    class Meta:
        model = Paper
        # Fields that should NOT be editable by the user directly through this form.
        # These will be populated by:
        # - The system (submitted_by, upload_date, last_updated)
        # - Web of Science API (wos_ut_id, actual_citation_count, last_wos_update)
        # - Automated Feature Extraction (all 'extracted_' fields, tf_idf_vector)
        # - Machine Learning Models (all 'predicted_' and 'visibility_' fields, key_feature_contributions)
        exclude = (
            'submitted_by',
            'wos_ut_id',
            'actual_citation_count',
            'last_wos_update',
            'venue_h_index',
            'venue_i10_index',
            'venue_impact_factor',
            'abstract_readability_score',
            'title_length',
            'keyword_relevance_score',
            'tf_idf_vector',
            'predicted_citations_2y',
            'prediction_confidence_interval_low',
            'prediction_confidence_interval_high',
            'visibility_category',
            'key_feature_contributions',
            'upload_date',
            'last_updated',
        )

        # Customize widgets for better user experience
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter paper title'}),
            'abstract': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Enter paper abstract'}),
            'keywords': forms.TextInput(attrs={'placeholder': 'Comma-separated keywords'}),
            'venue_name': forms.TextInput(attrs={'placeholder': 'e.g., IEEE Transactions on Pattern Analysis and Machine Intelligence'}),
            'publication_year': forms.NumberInput(attrs={'placeholder': 'e.g., 2023', 'min': 1900, 'max': 2100}),
            # pdf_file widget is handled by default for FileField
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make abstract and keywords optional if pdf_file is provided.
        # This logic often happens in the view after form submission.
        # However, you can hint it here.
        # self.fields['abstract'].required = False
        # self.fields['keywords'].required = False

        # Add help text or other attributes
        self.fields['pdf_file'].help_text = "Upload a PDF file of your research paper. Metadata will be extracted automatically."
        self.fields['title'].help_text = "Required if no PDF is uploaded, or to override extracted title."
        self.fields['abstract'].help_text = "Required if no PDF is uploaded, or to override extracted abstract."
        self.fields['keywords'].help_text = "Required if no PDF is uploaded, or to override extracted keywords."
        self.fields['venue_name'].help_text = "The name of the journal or conference where the paper was published."
        self.fields['publication_year'].help_text = "The year the paper was published."

    def clean(self):
        cleaned_data = super().clean()
        pdf_file = cleaned_data.get('pdf_file')
        title = cleaned_data.get('title')
        abstract = cleaned_data.get('abstract')
        keywords = cleaned_data.get('keywords')
        venue_name = cleaned_data.get('venue_name')
        publication_year = cleaned_data.get('publication_year')

        # Custom validation: Require title, abstract, keywords, venue, and year
        # if no PDF file is provided.
        if not pdf_file:
            if not title:
                self.add_error('title', "Title is required if no PDF is uploaded.")
            if not abstract:
                self.add_error('abstract', "Abstract is required if no PDF is uploaded.")
            if not keywords:
                self.add_error('keywords', "Keywords are required if no PDF is uploaded.")
            if not venue_name:
                self.add_error('venue_name', "Venue Name is required if no PDF is uploaded.")
            if not publication_year:
                self.add_error('publication_year', "Publication Year is required if no PDF is uploaded.")
        
        return cleaned_data