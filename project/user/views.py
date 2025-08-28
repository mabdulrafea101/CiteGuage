import json
import os
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from urllib.parse import urlencode
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login as auth_login
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import numpy as np

from .models import CustomUser, ResearcherProfile, Paper, WOSSearchHistory, WOSLightGBMPrediction
from .forms import CustomUserCreationForm, ResearcherProfileForm, PaperForm, CustomAuthenticationForm, WOSSearchForm
from .WOS_utils import (
    search_papers_wos,
    extract_title,
    extract_publication_year,
    extract_pubtype,
)
from .ml_utils import predict_from_text, MLModelError


# ----------------- SIGNUP -----------------


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'user/signup.html'
    
    def form_valid(self, form):
        try:
            # The custom form's save method handles first/last name.
            # The post_save signal handles profile creation.
            # The default form_valid saves the form and redirects.
            response = super().form_valid(form)

            messages.success(
                self.request,
                f'Account created successfully for {form.instance.email}. Please log in.'
            )
            return response

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

        publication_year_str = request.POST.get('publication_year', '').strip()
        publication_year = int(publication_year_str) if publication_year_str.isdigit() else None
        keywords = request.POST.get('keywords', '').strip()

        paper = Paper.objects.create(
            user=profile.user,
            title=title,
            category=category,
            document=document,
            abstract="",  # Assuming abstract is extracted later
            keywords=keywords,
            publication_year=publication_year
        )

        return JsonResponse({'success': True, 'message': 'Paper uploaded successfully!', 'paper_id': paper.id})

    except ResearcherProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Please create your researcher profile first.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


@login_required
def _get_prediction_for_wos_paper(request):
    """
    Helper function to handle the prediction logic for a WOS paper.
    Extracts paper data from the POST request, engineers features,
    and calls the ML model.
    """
    try:
        title = request.POST.get("title")
        abstract = request.POST.get("abstract")
        keywords_str = request.POST.get("keywords", "")

        # --- Feature Engineering from POST data ---
        publication_year_str = request.POST.get("publication_year")
        doi = request.POST.get("doi")
        url = request.POST.get("url")
        num_references_str = request.POST.get("num_references")

        # 1. Text-based feature lengths
        title_length = len(title) if title else 0
        abstract_length = len(abstract) if abstract else 0
        
        # 2. Keyword count from comma-separated string
        if keywords_str:
            keywords_list = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
            num_keywords = len(keywords_list)
        else:
            num_keywords = 0
        
        # 3. Paper age
        try:
            publication_year = int(publication_year_str)
            age = max(0, datetime.datetime.now().year - publication_year)
        except (ValueError, TypeError):
            age = 0

        # 4. Other numerical/binary features
        num_references = int(num_references_str) if num_references_str and num_references_str.isdigit() else 0
        has_doi = 1 if doi and doi.strip() and doi.lower() != 'none' else 0
        has_url = 1 if url and url.strip() and url.lower() != 'none' else 0

        numerical_features = np.array([
            title_length, abstract_length, num_keywords, age, num_references, has_doi, has_url
        ], dtype=np.float32)

        return predict_from_text(title, abstract, keywords_str, numerical_features)

    except (ValueError, MLModelError) as e:
        messages.error(request, f"Could not generate prediction: {e}")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred during prediction: {e}")
    return None

@login_required
def light_gbm_predict_wos_paper_view(request):
    """
    Calculates a prediction, saves it to the database, and redirects
    back to the search results page.
    """
    if request.method == "POST":
        uid = request.POST.get("uid")
        original_citations_str = request.POST.get("citations")

        if not uid:
            messages.error(request, "Missing paper UID for prediction.")
            return redirect('wos_papers')

        try:
            original_citations = int(original_citations_str) if original_citations_str and original_citations_str.isdigit() else 0
            # Note: The view is named for LightGBM, but the available helper `_get_prediction_for_wos_paper`
            # seems to implement a different model's logic. Using it as a more reasonable placeholder than random numbers.
            prediction_result = _get_prediction_for_wos_paper(request)

            if prediction_result:
                predicted_citations = prediction_result.get('predicted')

                WOSLightGBMPrediction.objects.update_or_create(
                    user=request.user,
                    wos_uid=uid,
                    defaults={
                        'original_citations': original_citations,
                        'light_gbm_predicted_citations': round(predicted_citations),
                        'light_gbm_percentage': 0,  # This field is no longer relevant with the new logic
                        'predicted_at': timezone.now()
                    }
                )
                messages.success(request, f"Prediction saved: {round(predicted_citations)} citations for UID {uid}.")

        except (ValueError, TypeError):
            messages.error(request, "Invalid citation count for LightGBM prediction.")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred while saving LightGBM prediction: {e}")

        # To reload the page with the same search results, we must pass the search parameters back.
        query_params = {
            'light_gbm_predicted_uid': uid,
            'search_field': request.POST.get("search_field"),
            'query': request.POST.get("query"),
            'count': request.POST.get("count")
        }
        query_params = {k: v for k, v in query_params.items() if v} # Keep URL clean
        redirect_url = f"{reverse('wos_papers')}?{urlencode(query_params)}"
        return redirect(redirect_url)

    return redirect('wos_papers')

@login_required
def wos_paper_list_view(request):
    # Initialize context variables
    form = WOSSearchForm()
    papers = []
    search_history = WOSSearchHistory.objects.filter(user=request.user).order_by('-searched_at')[:10]
    prediction = None
    predicted_paper_uid = None
    light_gbm_predictions_map = {}

    search_field = ""
    query = ""
    count = ""

    if request.method == "POST":
        form = WOSSearchForm(request.POST)
        action = request.POST.get("action")

        # --- Prediction Logic ---
        if action == "predict":
            predicted_paper_uid = request.POST.get("uid")
            prediction = _get_prediction_for_wos_paper(request)
            if prediction:
                title = request.POST.get("title", "paper")
                messages.success(request, f"Prediction successful for paper: '{title[:30]}...'.")

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
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                raw_dir = os.path.join(base_dir, "json_data", date_dir)
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
        # --- GET Request Logic: Handle history view or search from URL params ---
        view_history_id = request.GET.get("view_history")
        form = WOSSearchForm(request.GET or None)

        if view_history_id:
            try:
                search = get_object_or_404(WOSSearchHistory, id=view_history_id, user=request.user)
                if search.json_file_path and os.path.exists(search.json_file_path):
                    with open(search.json_file_path, "r", encoding="utf-8") as f:
                        papers = json.load(f)
                    messages.success(request, f"Loaded results for query: '{search.query}'")
                    # Pre-fill form with historical data
                    form = WOSSearchForm(initial=search.__dict__)
                else:
                    messages.error(request, "Saved result file not found.")
            except Exception as e:
                messages.error(request, f"Could not load search history: {e}")
        
        # Handle search from GET params (e.g., after LightGBM predict redirect)
        elif 'query' in request.GET and form.is_valid():
            search_field = form.cleaned_data["search_field"]
            query = form.cleaned_data["query"]
            count = form.cleaned_data["count"]
            papers = search_papers_wos(query=query, count=count, field=search_field)
            if not papers:
                messages.info(request, "No papers found for your query.")
        else:
            form = WOSSearchForm() # Reset to empty form if no action

    # After fetching or loading papers, retrieve all LightGBM predictions for them
    if papers:
        uids = [p.get('uid') for p in papers if p.get('uid')]
        all_light_gbm_preds = WOSLightGBMPrediction.objects.filter(user=request.user, wos_uid__in=uids).order_by('-predicted_at')
        for pred in all_light_gbm_preds:
            light_gbm_predictions_map.setdefault(pred.wos_uid, []).append(pred)
    
    return render(request, "user/wos_paper_list.html", {
        "form": form,
        "papers": papers,
        "search_history": search_history,
        "prediction": prediction,
        "predicted_paper_uid": predicted_paper_uid,
        "search_field": form.cleaned_data.get('search_field', '') if form.is_valid() else form.initial.get('search_field', ''),
        "query": form.cleaned_data.get('query', '') if form.is_valid() else form.initial.get('query', ''),
        "count": form.cleaned_data.get('count', '') if form.is_valid() else form.initial.get('count', ''),
        "light_gbm_predictions_map": light_gbm_predictions_map,
        "light_gbm_predicted_uid": request.GET.get("light_gbm_predicted_uid"),
    })

@login_required
def list_json_files_view(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_data_dir = os.path.join(base_dir, "json_data")
    json_files_data = []
    
    if not os.path.exists(json_data_dir):
        messages.warning(request, "The 'json_data' directory does not exist.")
        return render(request, 'user/json_file_list.html', {'files': []})

    for root, dirs, files in os.walk(json_data_dir):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    file_stat = os.stat(file_path)
                    # Make path relative to BASE_DIR for display
                    relative_path = os.path.relpath(file_path, base_dir)
                    file_info = {
                        'name': file,
                        'path': relative_path,
                        'full_path': file_path,
                        'size': file_stat.st_size,
                        'modified_time': datetime.datetime.fromtimestamp(file_stat.st_mtime)
                    }
                    json_files_data.append(file_info)
                except OSError as e:
                    messages.error(request, f"Could not access file {file_path}: {e}")

    # Sort files by modification time, newest first
    json_files_data.sort(key=lambda x: x['modified_time'], reverse=True)

    return render(request, 'user/json_file_list.html', {'files': json_files_data})

@login_required
def json_file_detail_view(request):
    file_path = request.GET.get("file")

    if not file_path:
        messages.error(request, "No file specified.")
        return redirect("json_file_list")
        
    # Security check: ensure the file is within the json_data directory
    abs_file_path = os.path.abspath(file_path)
    json_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "json_data")
    if not abs_file_path.startswith(os.path.abspath(json_data_dir)):
        messages.error(request, "Access to this file is not permitted.")
        return redirect("json_file_list")

    if not os.path.exists(abs_file_path):
        messages.error(request, f"File not found: {os.path.basename(file_path)}")
        return redirect("json_file_list")

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        messages.error(request, f"Failed to load or parse JSON file: {e}")
        return redirect("json_file_list")

    # For pretty printing in the template
    records_pretty = json.dumps(records, indent=4)

    context = {
        "file_name": os.path.basename(file_path),
        "records": records,
        "records_pretty": records_pretty
    }
    return render(request, "user/json_file_detail.html", context)

@login_required
def json_file_table_detail_view(request):
    file_path = request.GET.get("file")

    if not file_path:
        messages.error(request, "No file specified.")
        return redirect("json_file_list")
        
    # Security check: ensure the file is within the json_data directory
    abs_file_path = os.path.abspath(file_path)
    json_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "json_data")
    if not abs_file_path.startswith(os.path.abspath(json_data_dir)):
        messages.error(request, "Access to this file is not permitted.")
        return redirect("json_file_list")

    if not os.path.exists(abs_file_path):
        messages.error(request, f"File not found: {os.path.basename(file_path)}")
        return redirect("json_file_list")

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        messages.error(request, f"Failed to load or parse JSON file: {e}")
        return redirect("json_file_list")

    # The JSON files are already a list of parsed paper dicts
    if not isinstance(records, list):
        messages.error(request, "JSON file does not contain a list of records.")
        return redirect("json_file_list")

    # Extract tabular data
    papers_data = []
    for rec in records:
        if not isinstance(rec, dict):
            continue

        # Check if it's raw format (from WOS API) or parsed format
        if 'static_data' in rec:
            # Raw format from WOS API
            papers_data.append({
                'uid': rec.get('UID', 'N/A'),
                'title': extract_title(rec),
                'pubyear': extract_publication_year(rec),
                'pubtype': extract_pubtype(rec)
            })
        else:
            # Parsed format
            papers_data.append({
                'uid': rec.get('uid', 'N/A'),
                'title': rec.get('title', 'N/A'),
                'pubyear': rec.get('publication_year', 'N/A'),
                'pubtype': rec.get('pubtype', 'N/A')
            })

    context = {
        "file_name": os.path.basename(file_path),
        "papers": papers_data,
    }
    return render(request, "user/json_file_table_detail.html", context)

def _perform_paper_import(request, file_path):
    """Helper to import papers from a given JSON file path."""
    if not file_path or not os.path.exists(file_path):
        messages.error(request, "Invalid or non-existent file selected for import.")
        return 0, 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        messages.error(request, f"Failed to load or parse JSON file: {e}")
        return 0, 0

    if isinstance(records, dict):
        for key in ["records", "REC", "data"]:
            if key in records and isinstance(records[key], list):
                records = records[key]
                break
    
    if not isinstance(records, list):
        messages.error(request, "JSON file does not contain a list of records.")
        return 0, 0

    imported_count = 0
    skipped_count = 0
    user = request.user if request.user.is_authenticated else CustomUser.objects.first()

    for rec in records:
        if not isinstance(rec, dict):
            continue
            
        title = rec.get("title") or rec.get("TI") or rec.get("Title") or ""
        if not title:
            continue

        if Paper.objects.filter(title=title, user=user).exists():
            skipped_count += 1
            continue

        keywords_data = rec.get("keywords") or rec.get("DE") or ""
        keywords_str = ", ".join(keywords_data) if isinstance(keywords_data, list) else keywords_data

        Paper.objects.create(
            user=user,
            title=title,
            abstract=rec.get("abstract") or rec.get("AB") or "",
            keywords=keywords_str,
            publication_year=rec.get("publication_year") or rec.get("PY") or None,
            category=rec.get("category") or rec.get("SO") or "",
            authors=", ".join(rec.get("authors", [])) if isinstance(rec.get("authors"), list) else rec.get("authors", ""),
            status="imported",
        )
        imported_count += 1
    
    return imported_count, skipped_count

def import_papers_from_json(request):
    # Path to your json_data folder
    json_data_dir = os.path.join(settings.BASE_DIR, "json_data")
    # List all JSON files (recursively, if needed)
    json_files = []
    for root, dirs, files in os.walk(json_data_dir):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

    file_to_import = request.GET.get("file")
    if file_to_import:
        imported_count, skipped_count = _perform_paper_import(request, file_to_import)
        if imported_count > 0:
            messages.success(request, f"Successfully imported {imported_count} new papers from {os.path.basename(file_to_import)}.")
        if skipped_count > 0:
            messages.info(request, f"Skipped {skipped_count} papers that already exist in your collection.")
        if imported_count == 0 and skipped_count == 0:
            messages.warning(request, f"No new papers were imported from {os.path.basename(file_to_import)}. The file might be empty or contain only existing papers.")
        return redirect("json_file_list")

    if request.method == "POST":
        selected_file = request.POST.get("json_file")
        imported_count, skipped_count = _perform_paper_import(request, selected_file)
        return redirect("import_papers_from_json")

    return render(request, "user/import_papers_from_json.html", {
        "json_files": json_files,
        "selected_file": request.GET.get("file")
    })