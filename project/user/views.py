import json
from pprint import pprint
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .models import CustomUser, ResearcherProfile, Paper
from .forms import CustomUserCreationForm, ResearcherProfileForm, PaperForm, CustomAuthenticationForm, WOSSearchForm
from .WOS_utils import search_papers_wos


# ----------------- SIGNUP -----------------


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'user/signup.html'
    
    def form_valid(self, form):
        try:
            # Save user and also store first/last name from form
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.save()

            # Create profile for user (only with fields that exist)
            ResearcherProfile.objects.create(
                user=user,
                institution="",
                bio=""
            )

            messages.success(
                self.request,
                f'Account created successfully for {user.email}. Please log in.'
            )
            return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f"Error during signup: {e}")
            return redirect('signup')


# ----------------- LOGIN -----------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard' if not request.user.is_staff else 'admin:index')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect(request.GET.get('next', 'dashboard'))
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'user/login.html', {'form': form})



# ----------------- RESEARCHER PROFILE -----------------
class ResearcherProfileCreateView(LoginRequiredMixin, CreateView):
    model = ResearcherProfile
    form_class = ResearcherProfileForm
    template_name = 'user/create_profile.html'
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Your profile has been created successfully!')
        return super().form_valid(form)


class ResearcherProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = ResearcherProfile
    form_class = ResearcherProfileForm
    template_name = 'user/update_profile.html'
    success_url = reverse_lazy('researcher_profile')
    
    def get_object(self):
        return get_object_or_404(ResearcherProfile, user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully!')
        return super().form_valid(form)


class ResearcherProfileDetailView(LoginRequiredMixin, DetailView):
    model = ResearcherProfile
    template_name = 'user/profile_detail.html'
    context_object_name = 'profile'
    
    def get_object(self):
        return get_object_or_404(ResearcherProfile, user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['papers'] = Paper.objects.filter(user=self.get_object().user)
        return context


# ----------------- PAPER MANAGEMENT -----------------
class PaperCreateView(LoginRequiredMixin, CreateView):
    model = Paper
    form_class = PaperForm
    template_name = 'user/upload_paper.html'
    success_url = reverse_lazy('my_papers')
    
    def form_valid(self, form):
        try:
            form.instance.researcher = self.request.user.researcher_profile
            messages.success(self.request, 'Your paper has been uploaded successfully!')
            return super().form_valid(form)
        except ResearcherProfile.DoesNotExist:
            messages.error(self.request, 'Please create your researcher profile first.')
            return redirect('create_profile')
        except Exception as e:
            messages.error(self.request, f"Error uploading paper: {e}")
            return redirect('my_papers')


class PaperListView(LoginRequiredMixin, ListView):
    model = Paper
    template_name = 'user/my_papers.html'
    context_object_name = 'papers'
    
    def get_queryset(self):
        try:
            return Paper.objects.filter(user=self.request.user)
        except CustomUser.DoesNotExist:
            return Paper.objects.none()


@login_required
def upload_my_paper(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

    try:
        profile = get_object_or_404(ResearcherProfile, user=request.user)
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', '').strip()
        document = request.FILES.get('document')

        # Validation
        if not title:
            return JsonResponse({'success': False, 'message': 'Title is required.'})
        if not category:
            return JsonResponse({'success': False, 'message': 'Category is required.'})
        if not document:
            return JsonResponse({'success': False, 'message': 'Document is required.'})

        paper = Paper.objects.create(
    user=profile.user,
    title=title,
    abstract="",
    keywords=keywords or "",
    publication_year=publication_year
)



        return JsonResponse({'success': True, 'message': 'Paper uploaded successfully!', 'paper_id': paper.id})

    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Please create your researcher profile first.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})







# WOS View API end-points



def wos_paper_list_view(request):
    papers = []
    if request.method == "POST":
        form = WOSSearchForm(request.POST)
        if form.is_valid():
            field = form.cleaned_data["search_field"]
            query = form.cleaned_data["query"]
            count = form.cleaned_data["count"]

            papers = search_papers_wos(query=query, count=count, field=field)
            
    else:
        form = WOSSearchForm()

    return render(request, "user/wos_paper_list.html", {"form": form, "papers": papers})
