from django.urls import path
from .views import (
    SignUpView,
    login_view,
    ResearcherProfileCreateView,
    ResearcherProfileUpdateView,
    ResearcherProfileDetailView,
    MyPapersView,
    EditPaperView,
    wos_paper_list_view,
    light_gbm_predict_wos_paper_view,
    import_papers_from_json,
    json_file_detail_view,
    json_file_table_detail_view,
    list_json_files_view,
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
    path('papers/', MyPapersView.as_view(), name='my_papers'),
    path('papers/<int:pk>/edit/', EditPaperView.as_view(), name='edit_paper'),

    path("wos-papers/", wos_paper_list_view, name="wos_papers"),  # List papers from WOS
    path("papers/import-json/", import_papers_from_json, name="import_papers_from_json"),
    path("json-files/table-detail/", json_file_table_detail_view, name="json_file_table_detail"),
    path("json-files/detail/", json_file_detail_view, name="json_file_detail"),
    path("json-files/", list_json_files_view, name="json_file_list"),
    path("wos-papers/light-gbm-predict/", light_gbm_predict_wos_paper_view, name="light_gbm_predict_wos_papers"),
]
