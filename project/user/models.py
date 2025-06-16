from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


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
    
    # Add custom related_name attributes to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='custom_user_set',  # Changed from default 'user_set'
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='custom_user_set',  # Changed from default 'user_set'
        related_query_name='user',
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email


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
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    institution = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    position = models.CharField(max_length=50, choices=ACADEMIC_POSITIONS)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    
    # Academic Metrics
    h_index = models.IntegerField(default=0, help_text="The h-index measures both productivity and citation impact")
    i10_index = models.IntegerField(default=0, help_text="Number of publications with at least 10 citations")
    citation_count = models.IntegerField(default=0, help_text="Total number of citations")
    total_publications = models.IntegerField(default=0)
    
    # Research Areas (could be implemented as M2M with a separate ResearchArea model)
    research_interests = models.TextField(blank=True, help_text="Comma-separated list of research interests")
    
    # Social & Academic Profiles
    orcid_id = models.CharField(max_length=19, blank=True, help_text="ORCID identifier (e.g., 0000-0002-1825-0097)")
    google_scholar_id = models.CharField(max_length=50, blank=True)
    research_gate_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def citation_per_paper(self):
        """Calculate average citations per paper."""
        if self.total_publications > 0:
            return round(self.citation_count / self.total_publications, 2)
        return 0


class ResearchPaper(models.Model):
    """Model to store research papers uploaded by researchers."""
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('under_review', 'Under Review'),
    )
    
    researcher = models.ForeignKey(ResearcherProfile, on_delete=models.CASCADE, related_name='papers')
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    authors = models.TextField(help_text="Comma-separated list of co-authors")
    document = models.FileField(upload_to='research_papers/')
    category = models.CharField(max_length=100)
    keywords = models.TextField(help_text="Comma-separated list of keywords")
    
    # Paper metrics
    citation_count = models.IntegerField(default=0)
    predicted_citations = models.IntegerField(default=0, help_text="AI-predicted citation count")
    confidence_score = models.FloatField(default=0.0, help_text="Confidence level of prediction (0-1)")
    
    # Status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    publication_date = models.DateField(blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title


class CitationPrediction(models.Model):
    """Model to store citation predictions for papers."""
    
    paper = models.ForeignKey(ResearchPaper, on_delete=models.CASCADE, related_name='predictions')
    predicted_citations_1y = models.IntegerField(default=0, help_text="Predicted citations in 1 year")
    predicted_citations_3y = models.IntegerField(default=0, help_text="Predicted citations in 3 years")
    predicted_citations_5y = models.IntegerField(default=0, help_text="Predicted citations in 5 years")
    h_index_contribution = models.FloatField(default=0.0, help_text="Predicted contribution to h-index")
    prediction_date = models.DateTimeField(auto_now_add=True)
    
    # Factors affecting prediction
    author_impact_factor = models.FloatField(default=0.0)
    journal_impact_factor = models.FloatField(default=0.0, null=True, blank=True)
    topic_relevance_score = models.FloatField(default=0.0)
    methodology_score = models.FloatField(default=0.0)
    
    # Explanations for the user
    prediction_explanation = models.TextField(blank=True)
    
    def __str__(self):
        return f"Prediction for {self.paper.title}"