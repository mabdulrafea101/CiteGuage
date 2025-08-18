from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, ResearcherProfile, Paper, WOSSearchHistory, ResearchPaper

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

@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_user_email', 'publication_year', 'upload_date')
    search_fields = ('title', 'keywords')
    list_filter = ('publication_year',)

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Submitted By'

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


@admin.register(ResearchPaper)
class ResearchPaperAdmin(admin.ModelAdmin):
    list_display = ['filename', 'user', 'title', 'file_type', 'file_size', 'uploaded_at', 'updated_at']
    list_filter = ['file_type', 'uploaded_at', 'updated_at']
    search_fields = ['filename', 'title', 'user__username', 'user__email']
    readonly_fields = ['uploaded_at', 'updated_at']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('user', 'filename', 'file_type', 'file_size')
        }),
        ('Content', {
            'fields': ('title', 'abstract', 'keywords')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
