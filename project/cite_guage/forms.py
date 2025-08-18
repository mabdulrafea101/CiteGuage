from django import forms
from user.models import ResearchPaper

class DocumentUploadForm(forms.Form):
    document = forms.FileField(
        widget=forms.FileInput(attrs={
            'accept': '.pdf,.docx,.txt',
            'class': 'form-control'
        }),
        help_text='Upload PDF, DOCX, or TXT files (max 10MB)'
    )

class ResearchPaperSearchForm(forms.Form):
    search_query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search papers by title, keywords, or filename...'
        })
    )
    file_type = forms.ChoiceField(
        choices=[('', 'All Types')] + [(ext, ext.upper()) for ext in ['pdf', 'docx', 'txt']],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

