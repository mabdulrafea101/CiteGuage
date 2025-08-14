from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, ResearcherProfile, Paper



class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users with email as the unique identifier."""
    
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        label=_("Email address"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'name@example.com'})
    )

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name in ['password1', 'password2']:
                field.widget.attrs['placeholder'] = '••••••••'


class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form that uses email as the username field."""
    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com',
            'required': True,
        })
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'required': True,
        })
    )


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email')


class ResearcherProfileForm(forms.ModelForm):
    """Form for editing ResearcherProfile model without name fields."""
    class Meta:
        model = ResearcherProfile
        fields = ['institution', 'bio']
        widgets = {
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Institution'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Short bio'}),
        }


class PaperForm(forms.ModelForm):
    """Form for uploading and editing paper details."""

    authors = forms.CharField(
        max_length=1000,
        required=False,
        help_text="Comma-separated list of author names (e.g., John Doe, Jane Smith)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., John Doe, Jane Smith'})
    )

    class Meta:
        model = Paper
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
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter paper title'}),
            'abstract': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Enter paper abstract'}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma-separated keywords'}),
            'venue_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Journal or conference name'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 2023', 'min': 1900, 'max': 2100}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pdf_file'].help_text = "Upload a PDF file of your research paper."
        self.fields['title'].help_text = "Required if no PDF is uploaded."
        self.fields['abstract'].help_text = "Required if no PDF is uploaded."
        self.fields['keywords'].help_text = "Required if no PDF is uploaded."
        self.fields['venue_name'].help_text = "Name of the journal or conference."
        self.fields['publication_year'].help_text = "Year of publication."

    def clean(self):
        cleaned_data = super().clean()
        pdf_file = cleaned_data.get('pdf_file')
        required_fields = ['title', 'abstract', 'keywords', 'venue_name', 'publication_year']

        if not pdf_file:
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f"{field.replace('_', ' ').capitalize()} is required if no PDF is uploaded.")

        return cleaned_data






# WOS Form

class PaperSearchForm(forms.Form):
    title = forms.CharField(
        label="Search Term",
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Enter keywords'})
    )

FIELD_CHOICES = [
    ('TS', 'Topic (TS)'),
    ('TI', 'Title (TI)'),
    ('SO', 'Source / Journal (SO)'),
    ('AU', 'Author (AU)'),
    ('DO', 'DOI (DO)'),
]

class WOSSearchForm(forms.Form):
    search_field = forms.ChoiceField(
        choices=FIELD_CHOICES,
        label="Search Field",
        required=True
    )
    query = forms.CharField(
        label="Search Query",
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Enter your search term"})
    )
    count = forms.IntegerField(
        label="Number of Results",
        min_value=1,
        max_value=50,
        initial=10
    )