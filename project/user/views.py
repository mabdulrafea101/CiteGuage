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
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
import numpy as np

from .models import CustomUser, ResearcherProfile, Paper, WOSSearchHistory
from .forms import CustomUserCreationForm, ResearcherProfileForm, PaperForm, CustomAuthenticationForm, WOSSearchForm
from .WOS_utils import search_papers_wos
from .ml_utils import predict_from_text, MLModelError


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

@login_required

def wos_paper_list_view(request):
    # Initialize context variables
    form = WOSSearchForm()
    papers = []
    search_history = WOSSearchHistory.objects.filter(user=request.user).order_by('-searched_at')[:10]
    prediction = None
    predicted_paper_uid = None

    # Defaults for hidden fields
    search_field = ""
    query = ""
    count = ""

    if request.method == "POST":
        form = WOSSearchForm(request.POST)
        action = request.POST.get("action")

        # --- Prediction Logic ---
        if action == "predict":
            try:
                uid = request.POST.get("uid")
                title = request.POST.get("title")
                abstract = request.POST.get("abstract")
                keywords_str = request.POST.get("keywords")  # This is a string representation of a list

                predicted_paper_uid = uid  # To highlight the predicted card

                # --- Feature Engineering ---
                # Get raw data passed from the template's hidden fields
                publication_year_str = request.POST.get("publication_year")
                doi = request.POST.get("doi")
                url = request.POST.get("url")
                num_references_str = request.POST.get("num_references")

                # 1. title_length
                title_length = len(title) if title else 0
                # 2. abstract_length
                abstract_length = len(abstract) if abstract else 0
                # 3. num_keywords
                try:
                    import ast
                    keywords_list = ast.literal_eval(keywords_str)
                    num_keywords = len(keywords_list) if isinstance(keywords_list, list) else 0
                except (ValueError, SyntaxError):
                    num_keywords = 0
                
                # 4. age
                try:
                    publication_year = int(publication_year_str)
                    current_year = datetime.datetime.now().year
                    age = max(0, current_year - publication_year)
                except (ValueError, TypeError):
                    age = 0  # Default if year is missing/invalid
                
                # 5. num_references
                try:
                    num_references = int(num_references_str)
                except (ValueError, TypeError):
                    num_references = 0
                
                # 6. has_doi (1 if DOI exists and is not 'None' or empty)
                has_doi = 1 if doi and doi.strip() and doi.lower() != 'none' else 0
                # 7. has_url (1 if URL exists and is not 'None' or empty)
                has_url = 1 if url and url.strip() and url.lower() != 'none' else 0

                # Create the numerical features array in the correct order
                numerical_features_array = np.array([
                    title_length, abstract_length, num_keywords, age, num_references, has_doi, has_url
                ], dtype=np.float32)

                prediction_result = predict_from_text(
                    title=title, abstract=abstract, keywords=keywords_str, numerical_features=numerical_features_array
                )
                prediction = prediction_result
                messages.success(request, f"Prediction successful for paper: '{title[:30]}...'.")

            except (ValueError, MLModelError) as e:
                messages.error(request, f"Could not generate prediction: {e}")
            except Exception:
                messages.error(request, "An unexpected error occurred during prediction.")

        # --- Search Logic (runs for both search and after prediction) ---
        if form.is_valid():
            search_field = form.cleaned_data["search_field"]
            query = form.cleaned_data["query"]
            count = form.cleaned_data["count"]

            # Fetch papers from WOS
            papers = search_papers_wos(query=query, count=count, field=search_field)

            if action != "predict":  # save only for fresh searches
                if not papers:
                    messages.info(request, "No papers found for your query.")
                else:
                    messages.success(request, f"Found {len(papers)} papers for your query.")

                # Save search results to file + DB
                date_dir = datetime.datetime.now().strftime("%Y%m%d")
                raw_dir = os.path.join(settings.BASE_DIR, "json_data", date_dir)
                os.makedirs(raw_dir, exist_ok=True)
                file_path = os.path.join(
                    raw_dir, f"records_{request.user.id}_{datetime.datetime.now().strftime('%H%M%S')}.json"
                )

                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(papers, f, indent=4, ensure_ascii=False)

                    WOSSearchHistory.objects.create(
                        user=request.user,
                        query=query,
                        search_field=search_field,
                        count=count,
                        json_file_path=file_path
                    )
                except Exception as e:
                    messages.error(request, f"Could not save search history: {e}")

    else:
        # --- GET Request Logic ---
        form = WOSSearchForm()
        view_history_id = request.GET.get("view_history")
        if view_history_id:
            try:
                search = get_object_or_404(WOSSearchHistory, id=view_history_id, user=request.user)
                if search.json_file_path and os.path.exists(search.json_file_path):
                    with open(search.json_file_path, "r", encoding="utf-8") as f:
                        papers = json.load(f)
                    messages.success(request, f"Loaded results for query: '{search.query}'")

                    # Fill form + hidden field defaults
                    form = WOSSearchForm(initial={
                        "search_field": search.search_field,
                        "query": search.query,
                        "count": search.count,
                    })
                    search_field, query, count = search.search_field, search.query, search.count
                else:
                    messages.error(request, "Saved result file not found.")
            except Exception as e:
                messages.error(request, f"Could not load search history: {e}")

    return render(request, "user/wos_paper_list.html", {
        "form": form,
        "papers": papers,
        "search_history": search_history,
        "prediction": prediction,
        "predicted_paper_uid": predicted_paper_uid,
        "search_field": search_field,
        "query": query,
        "count": count,
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
        return redirect("user/import_papers_from_json")

    return render(request, "user/import_papers_from_json.html", {
        "json_files": json_files,
    })


    history = get_object_or_404(WOSSearchHistory, id=history_id)

    if not history.json_file_path:
        return JsonResponse({"error": "No JSON file saved for this search"}, status=400)

    try:
        with open(history.json_file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        return JsonResponse({"error": f"Failed to load JSON: {str(e)}"}, status=500)

    # Auto-locate paper by UID in nested structure
    found_paper = None
    if isinstance(data, dict):
        records = data.get("data") or data.get("records") or []
    elif isinstance(data, list):
        records = data
    else:
        records = []

    for paper in records:
        if paper.get("uid") == uid:
            found_paper = paper
            break

    if not found_paper:
        raise Http404("Paper not found in JSON file")

    # Extract abstract
    abstract = found_paper.get("abstract") or found_paper.get("AB") or "No abstract available"

    # Extract keywords (check multiple levels)
    keywords_list = []
    for key in ["keywords", "keywords_plus"]:
        if key in found_paper:
            kw_data = found_paper[key]
            if isinstance(kw_data, dict) and "keyword" in kw_data:
                keywords_list.extend(kw_data["keyword"])
            elif isinstance(kw_data, list):
                keywords_list.extend(kw_data)

    response_data = {
        "uid": uid,
        "abstract": abstract,
        "keywords": keywords_list or ["No keywords available"],
    }
    return JsonResponse(response_data)
    paper = get_object_or_404(Paper, id=id)

    try:
        with open(paper.json_file.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract abstract
        abstract = data.get("abstract", "")

        # Extract keywords (auto-detect between "keywords" and "keywords_plus")
        keywords = []
        if "keywords" in data and "keyword" in data["keywords"]:
            keywords = data["keywords"]["keyword"]
        elif "keywords_plus" in data and "keyword" in data["keywords_plus"]:
            keywords = data["keywords_plus"]["keyword"]

        return JsonResponse({
            "abstract": abstract,
            "keywords": keywords
        })

    except Exception as e:
        raise Http404(f"Error loading JSON: {str(e)}")