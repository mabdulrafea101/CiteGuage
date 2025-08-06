# your_app_name/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, ResearcherProfile, Paper


# Inline for ResearcherProfile (to be displayed on CustomUser admin page)
class ResearcherProfileInline(admin.StackedInline):
    model = ResearcherProfile
    can_delete = False
    verbose_name_plural = 'researcher profile'
    fieldsets = (
        (None, {
            'fields': (
                ('first_name', 'last_name'),
                ('institution', 'department'),
                'position', 'bio', 'profile_picture'
            )
        }),
        ('Academic Metrics', {
            'fields': ('h_index', 'i10_index', 'citation_count', 'total_publications'),
            'description': "These metrics are for researcher's profile display, not directly used in paper prediction."
        }),
        ('Research Details', {
            'fields': ('research_interests',),
        }),
        ('External Profiles', {
            'fields': ('orcid_id', 'google_scholar_id', 'research_gate_url', 'website'),
        }),
    )


# Custom Admin for CustomUser (integrating ResearcherProfile)
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ResearcherProfileInline,) # Add the inline here

    # Override base UserAdmin fields
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

    # Custom fieldsets for user details (excluding username)
    add_fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


# Admin for Paper model
@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitted_by', 'venue_name', 'publication_year',
                    'actual_citation_count', 'predicted_citations_2y', 'visibility_category',
                    'upload_date', 'has_prediction')
    list_filter = ('submitted_by', 'venue_name', 'publication_year', 'visibility_category')
    search_fields = ('title', 'abstract', 'keywords', 'wos_ut_id', 'submitted_by__email')
    readonly_fields = ('upload_date', 'last_updated', 'actual_citation_count',
                       'predicted_citations_2y', 'prediction_confidence_interval_low',
                       'prediction_confidence_interval_high', 'visibility_category',
                       'key_feature_contributions')
    raw_id_fields = ('submitted_by',)
    
    # Define custom fieldsets for better organization
    fieldsets = (
        (None, {
            'fields': ('title', 'submitted_by', 'pdf_file', 'upload_date', 'last_updated'),
        }),
        ('Paper Details (User Input/Extracted from PDF)', {
            'fields': ('abstract', 'keywords', 'venue_name', 'publication_year'),
            'description': "Core paper metadata."
        }),
        ('Web of Science Data', {
            'fields': ('wos_ut_id', 'actual_citation_count', 'last_wos_update'),
            'description': "Real-time citation count and ID from WoS API."
        }),
        ('Automated Feature Extraction', {
            'fields': (
                ('venue_h_index', 'venue_i10_index', 'venue_impact_factor'), # Grouped
                ('abstract_readability_score', 'title_length'), # Grouped
                'keyword_relevance_score',
                'tf_idf_vector'
            ),
            'description': "Numerical features derived for the prediction models."
        }),
        ('Citation Prediction Results', {
            'fields': (
                'predicted_citations_2y',
                ('prediction_confidence_interval_low', 'prediction_confidence_interval_high'),
                'visibility_category',
                'key_feature_contributions'
            ),
            'description': "Outputs from the machine learning models."
        }),
    )