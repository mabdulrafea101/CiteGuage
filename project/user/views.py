from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages

from .models import CustomUser, ResearcherProfile, ResearchPaper
from .forms import CustomUserCreationForm, ResearcherProfileForm, ResearchPaperForm, CustomAuthenticationForm
# In your views.py file

from django.http import JsonResponse

from django.contrib.auth.decorators import login_required



class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'user/signup.html'
    
    def form_valid(self, form):
        # Save the user
        response = super().form_valid(form)
        
        # Create a basic profile for the user
        user = self.object
        ResearcherProfile.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Add a success message
        email = form.cleaned_data.get('email')
        messages.success(self.request, f'Account created successfully for {email}. Please log in.')
        
        return response



def login_view(request):
    # If user is already logged in, handle redirect based on user type
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin:index')  # Redirect to admin panel
        else:
            return redirect('dashboard')    # Redirect to researcher dashboard
        
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.first_name if user.first_name else user.email}!')
            
            # Redirect based on user type
            if user.is_staff:
                return redirect('admin:index')  # Redirect to admin panel
            else:
                # Get the next parameter if it exists, otherwise redirect to dashboard
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'user/login.html', {'form': form})


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
        context['papers'] = ResearchPaper.objects.filter(researcher=self.get_object())
        return context


class ResearchPaperCreateView(LoginRequiredMixin, CreateView):
    model = ResearchPaper
    form_class = ResearchPaperForm
    template_name = 'user/upload_paper.html'
    success_url = reverse_lazy('my_papers')
    
    def form_valid(self, form):
        try:
            profile = self.request.user.researcher_profile
            form.instance.researcher = profile
            messages.success(self.request, 'Your paper has been uploaded successfully!')
            return super().form_valid(form)
        except ResearcherProfile.DoesNotExist:
            messages.error(self.request, 'Please create your researcher profile first.')
            return redirect('create_profile')


class ResearchPaperListView(LoginRequiredMixin, ListView):
    model = ResearchPaper
    template_name = 'user/my_papers.html'
    context_object_name = 'papers'
    
    def get_queryset(self):
        try:
            profile = self.request.user.researcher_profile
            return ResearchPaper.objects.filter(researcher=profile)
        except ResearcherProfile.DoesNotExist:
            return ResearchPaper.objects.none()




@login_required
def upload_paper(request):
    if request.method == 'POST':
        try:
            # Get the researcher profile
            profile = get_object_or_404(ResearcherProfile, user=request.user)
            
            # Get form data
            title = request.POST.get('title', '').strip()
            category = request.POST.get('category', '').strip()
            document = request.FILES.get('document')
            
            # Validate data
            if not title:
                return JsonResponse({'success': False, 'message': 'Please provide a title for your paper.'})
            
            if not category:
                return JsonResponse({'success': False, 'message': 'Please select a category for your paper.'})
            
            if not document:
                return JsonResponse({'success': False, 'message': 'Please upload a document file.'})
            
            # Create new paper record
            paper = ResearchPaper(
                researcher=profile,
                title=title,
                category=category,
                document=document,
                # Set default values for other required fields
                abstract="",  # You might want to extract this from the document later
                authors=profile.full_name(),  # Default to the researcher's name
                status='draft'
            )
            paper.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'Your paper was uploaded successfully!',
                'paper_id': paper.id
            })
            
        except ResearcherProfile.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'message': 'Please create your researcher profile first.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
