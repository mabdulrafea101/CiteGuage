from django.urls import path

from .views import (
    DashboardView,
    DocumentProcessorView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('upload-document/', DocumentProcessorView.as_view(), name='upload_document'),
]