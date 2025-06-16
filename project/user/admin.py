from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, ResearcherProfile, ResearchPaper, CitationPrediction

class ResearcherProfileInline(admin.StackedInline):
    model = ResearcherProfile
    can_delete = False
    verbose_name_plural = 'Researcher Profile'

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active',)
    list_filter = ('is_staff', 'is_active',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    inlines = (ResearcherProfileInline,)

class ResearchPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'researcher', 'status', 'citation_count', 'predicted_citations', 'upload_date')
    list_filter = ('status', 'category')
    search_fields = ('title', 'abstract', 'keywords', 'researcher__first_name', 'researcher__last_name')
    date_hierarchy = 'upload_date'

class CitationPredictionAdmin(admin.ModelAdmin):
    list_display = ('paper', 'predicted_citations_1y', 'predicted_citations_3y', 'prediction_date')
    list_filter = ('prediction_date',)
    search_fields = ('paper__title', 'prediction_explanation')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(ResearcherProfile)
admin.site.register(ResearchPaper, ResearchPaperAdmin)
admin.site.register(CitationPrediction, CitationPredictionAdmin)