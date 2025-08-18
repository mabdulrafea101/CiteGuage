import json
from pprint import pprint
import os
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .models import CustomUser, ResearcherProfile, Paper, WOSSearchHistory
from .forms import CustomUserCreationForm, ResearcherProfileForm, PaperForm, CustomAuthenticationForm, WOSSearchForm
from .WOS_utils import search_papers_wos


from django.conf import settings



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



# def wos_paper_list_view(request):
#     papers = []
#     if request.method == "POST":
#         form = WOSSearchForm(request.POST)
#         if form.is_valid():
#             field = form.cleaned_data["search_field"]
#             query = form.cleaned_data["query"]
#             count = form.cleaned_data["count"]

#             papers = search_papers_wos(query=query, count=count, field=field)
            
#     else:
#         form = WOSSearchForm()

#     return render(request, "user/wos_paper_list.html", {"form": form, "papers": papers})


def wos_paper_list_view(request):
    papers = []
    json_file_path = None
    json_data_to_display = None

    # Check if a specific search is being viewed
    view_json_id = request.GET.get("view_json")
    if view_json_id:
        try:
            search = WOSSearchHistory.objects.get(id=view_json_id, user=request.user)
            if search.json_file_path and os.path.exists(search.json_file_path):
                with open(search.json_file_path, "r", encoding="utf-8") as f:
                    json_data_to_display = json.load(f)
        except Exception as e:
            json_data_to_display = {"error": f"Could not load JSON: {e}"}

    if request.method == "POST":
        form = WOSSearchForm(request.POST)
        if form.is_valid():
            field = form.cleaned_data["search_field"]
            query = form.cleaned_data["query"]
            count = form.cleaned_data["count"]

            papers = search_papers_wos(query=query, count=count, field=field)

            # Save the search result as JSON file
            date_dir = datetime.datetime.now().strftime("%Y%m%d")
            raw_dir = os.path.join(os.getcwd(), "json_data", date_dir)
            os.makedirs(raw_dir, exist_ok=True)
            file_path = os.path.join(raw_dir, f"records_{datetime.datetime.now().strftime('%H%M%S')}.json")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(papers, f, indent=4, ensure_ascii=False)
                json_file_path = file_path
            except Exception as e:
                json_file_path = None  # Optionally, handle/log error

            # Save search history
            if request.user.is_authenticated:
                WOSSearchHistory.objects.create(
                    user=request.user,
                    query=query,
                    search_field=field,
                    count=count,
                    json_file_path=json_file_path
                )
    else:
        form = WOSSearchForm()

    search_history = []
    if request.user.is_authenticated:
        search_history = WOSSearchHistory.objects.filter(user=request.user).order_by('-searched_at')[:10]

    return render(request, "user/wos_paper_list.html", {
        "form": form,
        "papers": papers,
        "search_history": search_history,
        "json_data_to_display": json_data_to_display,
    })





def import_papers_from_json(request):
    # Path to your json_data folder
    json_data_dir = os.path.join(os.getcwd(), "json_data")
    # List all JSON files (recursively, if needed)
    json_files = []
    for root, dirs, files in os.walk(json_data_dir):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

    if request.method == "POST":
        selected_file = request.POST.get("json_file")
        if not selected_file or not os.path.exists(selected_file):
            messages.error(request, "Invalid file selected.")
            return redirect("import_papers_from_json")

        # Load JSON data
        with open(selected_file, "r", encoding="utf-8") as f:
            try:
                records = json.load(f)
            except Exception as e:
                messages.error(request, f"Failed to load JSON: {e}")
                return redirect("import_papers_from_json")

        # If the JSON is a dict with a list inside, extract it
        if isinstance(records, dict):
            # Try common keys
            for key in ["records", "REC", "data"]:
                if key in records:
                    records = records[key]
                    break

        if not isinstance(records, list):
            messages.error(request, "JSON file does not contain a list of records.")
            return redirect("import_papers_from_json")

        # Import each record
        imported = 0
        for rec in records:
            # Map fields from JSON to Paper model
            title = rec.get("title") or rec.get("TI") or rec.get("Title") or ""
            abstract = rec.get("abstract") or rec.get("AB") or ""
            keywords = rec.get("keywords") or rec.get("DE") or ""
            publication_year = rec.get("publication_year") or rec.get("PY") or None
            category = rec.get("category") or rec.get("SO") or ""
            authors = rec.get("authors") or rec.get("AU") or ""
            status = "imported"

            # If you want to assign to the current user, or a default user:
            user = request.user if request.user.is_authenticated else CustomUser.objects.first()

            # Avoid duplicates (optional): check by title and user
            if Paper.objects.filter(title=title, user=user).exists():
                continue

            Paper.objects.create(
                user=user,
                title=title,
                abstract=abstract,
                keywords=keywords,
                publication_year=publication_year,
                category=category,
                authors=", ".join(authors) if isinstance(authors, list) else authors,
                status=status,
            )
            imported += 1

        messages.success(request, f"Imported {imported} papers from {os.path.basename(selected_file)}.")
        return redirect("import_papers_from_json")

    return render(request, "user/import_papers_from_json.html", {
        "json_files": json_files,
    })