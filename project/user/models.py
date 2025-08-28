import random
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

# ---------------------------
# Custom User
# ---------------------------
class CustomUserManager(BaseUserManager):
    """Manager for CustomUser using email instead of username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email is required'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None  # if using email login
    email = models.EmailField(unique=True)

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email



# ---------------------------
# User Profile
# ---------------------------
class ResearcherProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='researcher_profile')
    institution = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email



# ---------------------------
# Paper & Predictions
# ---------------------------
class Paper(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='papers')
    title = models.CharField(max_length=500)
    abstract = models.TextField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)

    category = models.CharField(max_length=100, blank=True, null=True)
    document = models.FileField(upload_to='papers/', blank=True, null=True)
    authors = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=50, default='draft')

    predicted_citations_2y = models.IntegerField(blank=True, null=True)
    prediction_confidence_low = models.IntegerField(blank=True, null=True)
    prediction_confidence_high = models.IntegerField(blank=True, null=True)

    upload_date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.title

    @property
    def has_prediction(self):
        return self.predicted_citations_2y is not None




class WOSSearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wos_searches')
    query = models.CharField(max_length=255)
    search_field = models.CharField(max_length=20)
    count = models.IntegerField()
    searched_at = models.DateTimeField(auto_now_add=True)
    json_file_path = models.CharField(max_length=500, blank=True, null=True)  # Path to saved JSON file
    # Optionally, you can store the raw JSON data (not recommended for large results)
    # json_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} | {self.query} | {self.searched_at.strftime('%Y-%m-%d %H:%M:%S')}"
    

class WOSLightGBMPrediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wos_light_gbm_predictions')
    wos_uid = models.CharField(max_length=255, help_text="Web of Science UID of the paper")
    original_citations = models.IntegerField(help_text="Original citation count of the paper")
    light_gbm_percentage = models.IntegerField(default=random.randint(15, 30), help_text="Random percentage used for the prediction")
    light_gbm_predicted_citations = models.IntegerField(help_text="Citations predicted based on the LightGBM percentage")
    predicted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "WOS LightGBM Prediction"
        verbose_name_plural = "WOS LightGBM Predictions"
        ordering = ['-predicted_at']

    def __str__(self):
        return f"UID: {self.wos_uid} | LightGBM Predicted: {self.light_gbm_predicted_citations} | User: {self.user.email}"







CustomUser = get_user_model()

class ResearchPaper(models.Model):
    """
    Model to store research paper information extracted from uploaded documents
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='research_papers',
        help_text="User who uploaded the document"
    )
    filename = models.CharField(
        max_length=255,
        help_text="Original filename of the uploaded document"
    )
    title = models.TextField(
        help_text="Extracted or generated title from the document"
    )
    abstract = models.TextField(
        blank=True,
        null=True,
        help_text="Extracted abstract or summary from the document"
    )
    keywords = models.JSONField(
        default=list,
        help_text="List of extracted keywords from the document"
    )
    file_size = models.PositiveIntegerField(
        help_text="Size of the original file in bytes"
    )
    file_type = models.CharField(
        max_length=10,
        help_text="File extension (pdf, docx, txt)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        unique_together = ['user', 'filename']  # Prevent duplicate filenames per user
        indexes = [
            models.Index(fields=['user', 'filename']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return self.filename
    
    @property
    def keywords_as_string(self):
        """Return keywords as comma-separated string"""
        return ', '.join(self.keywords) if self.keywords else ''
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"