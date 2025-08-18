from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings


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