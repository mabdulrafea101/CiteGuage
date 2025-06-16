from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'cite_guage/dashboard.html'
    login_url = '/user/login/'  # Redirect to login if not authenticated
