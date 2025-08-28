from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, ResearcherProfile, WOSSearchHistory, ResearchPaper, WOSLightGBMPrediction, WOSRidgePrediction

# Inline for ResearcherProfile on the CustomUser admin page
class ResearcherProfileInline(admin.StackedInline):
    model = ResearcherProfile
    can_delete = False
    verbose_name_plural = 'Researcher Profile'
    fieldsets = (
        (None, {
            'fields': (
                'institution',
                'bio'
            )
        }),
    )

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ResearcherProfileInline,)
    list_display = ('email', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)
    add_fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# Register ResearcherProfile directly (for completeness, even though it's inline)
@admin.register(ResearcherProfile)
class ResearcherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution')
    search_fields = ('user__email', 'institution')

# Register WOSSearchHistory
@admin.register(WOSSearchHistory)
class WOSSearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'search_field', 'count', 'searched_at')
    search_fields = ('user__email', 'query', 'search_field')
    list_filter = ('search_field', 'searched_at')

@admin.register(WOSLightGBMPrediction)
class WOSLightGBMPredictionAdmin(admin.ModelAdmin):
    list_display = ('wos_uid', 'user', 'original_citations', 'light_gbm_predicted_citations', 'predicted_at')
    search_fields = ('wos_uid', 'user__email')
    list_filter = ('predicted_at',)


@admin.register(WOSRidgePrediction)
class WOSRidgePredictionAdmin(admin.ModelAdmin):
    list_display = ('wos_uid', 'user', 'predicted_citations', 'ci_low', 'ci_high', 'predicted_at')
    search_fields = ('wos_uid', 'user__email')
    list_filter = ('predicted_at',)


@admin.register(ResearchPaper)
class ResearchPaperAdmin(admin.ModelAdmin):
    list_display = ['filename', 'user', 'title', 'file_type', 'publication_year', 'status', 'uploaded_at']
    list_filter = ['file_type', 'publication_year', 'status', 'uploaded_at', 'updated_at']
    search_fields = ['filename', 'title', 'user__username', 'user__email', 'keywords', 'authors']
    readonly_fields = ['uploaded_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('user', 'filename', 'file_type', 'file_size')
        }),
        ('Extracted Content', {
            'fields': ('title', 'abstract', 'authors', 'keywords', 'publication_year')
        }),
        ('Status & Prediction', {
            'fields': ('status', 'predicted_citations', 'prediction_confidence_low', 'prediction_confidence_high', 'predicted_at')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
