from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField # Consider if you strictly need ArrayField (PostgreSQL only)


class CustomUserManager(BaseUserManager):
    """Define a model manager for custom User model with email as the unique identifier."""

    def create_user(self, email, password, **extra_fields):
        """Create and save a regular User with the given email and password."""
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """Custom User model that uses email as the unique identifier instead of username."""
    
    username = None
    email = models.EmailField(_('email address'), unique=True)
    
    # Add custom related_name attributes to avoid clashes with Django's default User model
    # when you have a custom user model. These are good.
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='custom_user_set', # Changed from default 'user_set'
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set', # Changed from default 'user_set'
        related_query_name='user',
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email

    # Add role properties for easier access control
    @property
    def is_admin(self):
        return self.is_staff and self.is_superuser # Or you can define specific groups/roles

    @property
    def is_researcher(self):
        # All authenticated non-admin users could be considered researchers,
        # or you might add a specific group for researchers.
        return not self.is_admin and self.is_active


class ResearcherProfile(models.Model):
    """Extended profile for researchers with academic metrics."""
    
    ACADEMIC_POSITIONS = (
        ('professor', 'Professor'),
        ('associate_professor', 'Associate Professor'),
        ('assistant_professor', 'Assistant Professor'),
        ('lecturer', 'Lecturer'),
        ('research_fellow', 'Research Fellow'),
        ('postdoc', 'Post-Doctoral Researcher'),
        ('phd_student', 'PhD Student'),
        ('masters_student', 'Masters Student'),
        ('other', 'Other'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='researcher_profile')
    first_name = models.CharField(max_length=100, blank=True) # Allow blank for initial registration
    last_name = models.CharField(max_length=100, blank=True)  # Allow blank
    institution = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=50, choices=ACADEMIC_POSITIONS, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    
    # Academic Metrics (for display on researcher profile, NOT for paper prediction inputs as per scope)
    h_index = models.IntegerField(default=0, help_text="The h-index measures both productivity and citation impact")
    i10_index = models.IntegerField(default=0, help_text="Number of publications with at least 10 citations")
    citation_count = models.IntegerField(default=0, help_text="Total number of citations")
    total_publications = models.IntegerField(default=0)
    
    # Research Areas
    research_interests = models.TextField(blank=True, help_text="Comma-separated list of research interests")
    
    # Social & Academic Profiles
    orcid_id = models.CharField(max_length=19, blank=True, help_text="ORCID identifier (e.g., 0000-0002-1825-0097)")
    google_scholar_id = models.CharField(max_length=50, blank=True)
    research_gate_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.full_name() or self.user.email}" # Use email if names not set
    
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return "" # Return empty string if names are not set
    
    @property
    def citation_per_paper(self):
        """Calculate average citations per paper."""
        if self.total_publications > 0:
            return round(self.citation_count / self.total_publications, 2)
        return 0


class Paper(models.Model): # Renamed from ResearchPaper for brevity and clarity based on scope
    """Model to store research papers and their extracted features and prediction results."""
    
    # A. User Management & Access Control
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='submitted_papers') # Link to CustomUser

    # B. Paper Handling & Feature Extraction (input data)
    title = models.CharField(max_length=500) # Increased max_length
    abstract = models.TextField(blank=True, null=True) # Can be extracted or manually input
    keywords = models.TextField(help_text="Comma-separated list of keywords", blank=True, null=True) # Can be extracted or manually input
    venue_name = models.CharField(max_length=200, blank=True, null=True) # Name of journal/conference
    publication_year = models.IntegerField(blank=True, null=True) # From metadata

    # B. Paper Handling & Feature Extraction (file storage)
    pdf_file = models.FileField(upload_to='papers/pdfs/', blank=True, null=True) # Upload PDF
    # If using manual input, pdf_file would be null.

    # B. Paper Handling & Feature Extraction (extracted/fetched features)
    wos_ut_id = models.CharField(max_length=50, blank=True, null=True, unique=True, # Web of Science Unique ID for direct lookup
                                 help_text="Web of Science Accession Number (UT)")
    
    # Venue metrics (from WoS Journals API or pre-computed)
    venue_h_index = models.FloatField(blank=True, null=True) # Can be difficult to get from WoS API directly for all venues
    venue_i10_index = models.FloatField(blank=True, null=True) # Can be difficult to get from WoS API directly for all venues
    venue_impact_factor = models.FloatField(blank=True, null=True, help_text="Journal Impact Factor from WoS JCR")
    
    # Abstract/Title features
    abstract_readability_score = models.FloatField(blank=True, null=True) # e.g., Flesch–Kincaid
    title_length = models.IntegerField(blank=True, null=True)
    keyword_relevance_score = models.FloatField(blank=True, null=True) # Calculated internally

    # Text vectors for ML model
    # Storing as JSONField is suitable for Python lists/arrays.
    # If using PostgreSQL and strict arrays, ArrayField might be considered, but JSONField is more flexible.
    tf_idf_vector = models.JSONField(blank=True, null=True, help_text="TF-IDF vector or lightweight embedding of paper text")

    # C. Machine Learning & Prediction (raw citation count from WoS)
    actual_citation_count = models.IntegerField(default=0, help_text="Current number of citations from Web of Science")
    last_wos_update = models.DateTimeField(blank=True, null=True, help_text="Timestamp of last successful WoS citation fetch")

    # D. System Integration & User Dashboard (prediction results)
    predicted_citations_2y = models.IntegerField(blank=True, null=True, help_text="Predicted citations in 2 years")
    prediction_confidence_interval_low = models.IntegerField(blank=True, null=True)
    prediction_confidence_interval_high = models.IntegerField(blank=True, null=True)
    
    # Classification model output
    VISIBILITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )
    visibility_category = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, blank=True, null=True)
    
    # Key feature contributions for visualizations
    key_feature_contributions = models.JSONField(blank=True, null=True, help_text="JSON object mapping feature names to their contribution scores")

    # General metadata
    upload_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paper"
        verbose_name_plural = "Papers"
        ordering = ['-upload_date']

    def __str__(self):
        return self.title

    # Property to indicate if prediction has been run
    @property
    def has_prediction(self):
        return self.predicted_citations_2y is not None


# Removed CitationPrediction model for now, as its fields are integrated into Paper.
# If you need to store multiple prediction versions over time for a single paper,
# then CitationPrediction would become relevant again, but with a different structure
# (e.g., storing a snapshot of prediction at a given date).
# For the current scope, one forward-looking prediction per paper seems sufficient
# to be stored directly on the Paper model.