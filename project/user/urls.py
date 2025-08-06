from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication URLs
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='user/password_reset.html'), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='user/password_reset_done.html'), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='user/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='user/password_reset_complete.html'), 
         name='password_reset_complete'),
    
    # Researcher profile URLs
    path('profile/', views.ResearcherProfileDetailView.as_view(), name='researcher_profile'),
    path('profile/create/', views.ResearcherProfileCreateView.as_view(), name='create_profile'),
    path('profile/update/', views.ResearcherProfileUpdateView.as_view(), name='update_profile'),
    
    # Research paper URLs
    path('papers/', views.PaperListView.as_view(), name='my_papers'),
    path('papers/upload/', views.PaperCreateView.as_view(), name='upload_my_paper'),
    path('papers/upload/ajax/', views.upload_paper, name='upload_paper'),
]
