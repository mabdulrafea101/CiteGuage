from django.urls import path
from .views import (
    SignUpView,
    login_view,
    ResearcherProfileCreateView,
    ResearcherProfileUpdateView,
    ResearcherProfileDetailView,
    PaperCreateView,
    PaperListView,
    upload_my_paper,
    wos_paper_list_view,
    import_papers_from_json
)
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Authentication
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # Researcher Profile
    path('profile/create/', ResearcherProfileCreateView.as_view(), name='create_profile'),
    path('profile/update/', ResearcherProfileUpdateView.as_view(), name='update_profile'),
    path('profile/', ResearcherProfileDetailView.as_view(), name='researcher_profile'),

    # Papers
    path('papers/upload/', PaperCreateView.as_view(), name='upload_paper_page'),  # form page
    path('papers/', PaperListView.as_view(), name='my_papers'),
    path('papers/api/upload/', upload_my_paper, name='upload_my_paper'),  # AJAX/JSON API endpoint

    path("wos-papers/", wos_paper_list_view, name="wos_papers"),  # List papers from WOS
    path("papers/import-json/", import_papers_from_json, name="import_papers_from_json"),
]
