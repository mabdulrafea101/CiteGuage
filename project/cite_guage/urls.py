from django.urls import path

from .views import (
    DashboardView,
    DocumentProcessorView,
    ResearchPaperDetail

)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('upload-document/', DocumentProcessorView.as_view(), name='upload_document'),
    path('research-paper/<int:pk>/', ResearchPaperDetail.as_view(), name='Research_paper_detail')
]