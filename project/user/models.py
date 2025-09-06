import random
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
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
        """Return the user's full name or email."""
        return self.get_full_name().strip() or self.email

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        return f"{self.first_name} {self.last_name}".strip()



# ---------------------------
# User Profile
# ---------------------------
def profile_picture_path(instance, filename):
    """Generate file path for new profile pictures."""
    # file will be uploaded to MEDIA_ROOT/profile_pics/user_<id>/<filename>
    return f'profile_pics/user_{instance.user.id}/{filename}'


class ResearcherProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='researcher_profile')

    # Personal & Professional Info
    profile_picture = models.ImageField(upload_to=profile_picture_path, blank=True, null=True)
    institution = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True, help_text="e.g., PhD Candidate, Assistant Professor")
    bio = models.TextField(blank=True)

    # Research Info
    research_interests = models.TextField(blank=True, help_text="Comma-separated list of interests")

    # External Links
    website = models.URLField(max_length=255, blank=True)
    orcid_id = models.CharField(max_length=50, blank=True, help_text="Format: 0000-0000-0000-0000")
    google_scholar_id = models.CharField(max_length=50, blank=True)
    research_gate_url = models.URLField(max_length=255, blank=True)

    # Metrics (can be populated later from external sources)
    h_index = models.PositiveIntegerField(default=0, blank=True)
    i10_index = models.PositiveIntegerField(default=0, blank=True)
    citation_count = models.PositiveIntegerField(default=0, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.email

    @property
    def full_name(self):
        """Returns the user's full name."""
        return self.user.get_full_name()

    @property
    def first_name(self):
        """Returns the user's first name."""
        return self.user.first_name

    @property
    def last_name(self):
        """Returns the user's last name."""
        return self.user.last_name

    @property
    def research_interests_list(self):
        """Returns a sorted list of research interests."""
        if not self.research_interests:
            return []
        return sorted([interest.strip() for interest in self.research_interests.split(',') if interest.strip()])

    @property
    def total_publications(self):
        return self.user.papers.count()




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
    light_gbm_percentage = models.IntegerField(help_text="Random percentage used for the prediction")
    light_gbm_predicted_citations = models.IntegerField(help_text="Citations predicted based on the LightGBM percentage")
    predicted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "WOS LightGBM Prediction"
        verbose_name_plural = "WOS LightGBM Predictions"
        ordering = ['-predicted_at']

    def __str__(self):
        return f"UID: {self.wos_uid} | LightGBM Predicted: {self.light_gbm_predicted_citations} | User: {self.user.email}"


class WOSRidgePrediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wos_ridge_predictions')
    wos_uid = models.CharField(max_length=255, help_text="Web of Science UID of the paper")
    predicted_citations = models.IntegerField(help_text="Citations predicted by the Ridge model")
    ci_low = models.FloatField(null=True, blank=True, help_text="Lower bound of the 95% confidence interval")
    ci_high = models.FloatField(null=True, blank=True, help_text="Upper bound of the 95% confidence interval")
    predicted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "WOS Ridge Prediction"
        verbose_name_plural = "WOS Ridge Predictions"
        ordering = ['-predicted_at']

    def __str__(self):
        return f"UID: {self.wos_uid} | Ridge Predicted: {self.predicted_citations} | User: {self.user.email}"




@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a researcher profile automatically when a new user is created."""
    if created:
        ResearcherProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """Save the profile when the user is saved."""
    if hasattr(instance, 'researcher_profile'):
        instance.researcher_profile.save()



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
    authors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of extracted authors from the document."
    )
    keywords = models.JSONField(
        default=list,
        help_text="List of extracted keywords from the document"
    )
    publication_year = models.IntegerField(blank=True, null=True, help_text="Extracted publication year.")
    category = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, default='draft', blank=True)
    file_size = models.PositiveIntegerField(
        help_text="Size of the original file in bytes"
    )
    file_type = models.CharField(
        max_length=10,
        help_text="File extension (pdf, docx, txt)"
    )

    # Prediction fields
    predicted_citations = models.IntegerField(
        blank=True, null=True,
        help_text="Predicted citation count for the next 2 years."
    )
    prediction_confidence_low = models.IntegerField(blank=True, null=True)
    prediction_confidence_high = models.IntegerField(blank=True, null=True)
    predicted_at = models.DateTimeField(blank=True, null=True)

    # LightGBM prediction fields
    light_gbm_predicted_citations = models.IntegerField(blank=True, null=True, help_text="Dummy LightGBM prediction")
    light_gbm_percentage = models.IntegerField(blank=True, null=True, help_text="[DEPRECATED] No longer used.")
    light_gbm_predicted_at = models.DateTimeField(blank=True, null=True)


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
        if size is None:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class ResearchPaperRidgePrediction(models.Model):
    research_paper = models.ForeignKey(ResearchPaper, on_delete=models.CASCADE, related_name='ridge_predictions')
    predicted_citations = models.IntegerField(help_text="Citations predicted by the Ridge model")
    ci_low = models.FloatField(null=True, blank=True, help_text="Lower bound of the 95% confidence interval")
    ci_high = models.FloatField(null=True, blank=True, help_text="Upper bound of the 95% confidence interval")
    predicted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-predicted_at']
        verbose_name = "Research Paper Ridge Prediction"

    def __str__(self):
        return f"Paper: {self.research_paper.id} | Predicted: {self.predicted_citations}"


class ResearchPaperLightGBMPrediction(models.Model):
    research_paper = models.ForeignKey(ResearchPaper, on_delete=models.CASCADE, related_name='light_gbm_predictions')
    light_gbm_predicted_citations = models.IntegerField(help_text="Citations predicted by the LightGBM model")
    predicted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-predicted_at']
        verbose_name = "Research Paper LightGBM Prediction"

    def __str__(self):
        return f"Paper: {self.research_paper.id} | Predicted: {self.light_gbm_predicted_citations}"