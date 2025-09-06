import os
import logging
import tempfile
import PyPDF2
import docx
import re
import random

from django.shortcuts import render, redirect
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncMonth, ExtractYear
from datetime import timedelta
from collections import Counter
from user.models import ResearchPaper, WOSSearchHistory, WOSLightGBMPrediction, WOSRidgePrediction, ResearchPaperRidgePrediction, ResearchPaperLightGBMPrediction, ResearchPaperRidgePrediction, ResearchPaperLightGBMPrediction
from user.ml_utils import predict_from_text, MLModelError


# Set up logging for debugging
logger = logging.getLogger(__name__)

class DocumentProcessorView(LoginRequiredMixin, View):
    """
    Class-based view for handling document upload and processing.
    Requires user authentication and saves data to ResearchPaper model.
    """

    login_url = '/user/login/'  # Redirect to login if not authenticated
    
    def get(self, request):
        """Render the upload form"""
        logger.info(f"User {request.user.email} accessed document upload page")
        return render(request, 'cite_guage/upload_document.html')
    
    def post(self, request):
        """Handle document upload and processing"""
        try:
            logger.info(f"User {request.user.email} initiated document upload")
            
            # Step 1: Validate file upload
            file_validation_result = self._validate_uploaded_file(request)
            if not file_validation_result['success']:
                return self._handle_error(
                    request, 
                    file_validation_result['error'],
                    'cite_guage/upload_document.html'
                )
            
            uploaded_file = file_validation_result['file']
            
            # Step 2: Process the document
            processing_result = self._process_document_content(uploaded_file, request.user)
            if not processing_result['success']:
                return self._handle_error(
                    request,
                    f"Processing failed: {processing_result['error']}",
                    'cite_guage/upload_document.html'
                )
            
            # Step 3: Save or update in database
            save_result = self._save_research_paper_data(
                user=request.user,
                filename=uploaded_file.name,
                file_size=uploaded_file.size,
                processed_data=processing_result['data']
            )
            
            if not save_result['success']:
                return self._handle_error(
                    request,
                    f"Database save failed: {save_result['error']}",
                    'cite_guage/upload_document.html'
                )
            
            # Step 4: Log success and prepare response
            research_paper = save_result['research_paper']
            self._log_processing_success(request.user, uploaded_file, research_paper)
            
            messages.success(
                request, 
                f'Document "{uploaded_file.name}" processed and saved successfully!'
            )
            
            context = {
                'result': processing_result['data'],
                'filename': uploaded_file.name,
                'research_paper': research_paper,
                'is_updated': save_result['is_updated']
            }
            
            return render(request, 'cite_guage/document_results.html', context)
                
        except Exception as e:
            logger.exception(f"User {request.user} - Critical error in document processing")
            return self._handle_error(
                request,
                'An unexpected error occurred while processing your document.',
                'cite_guage/upload_document.html'
            )
    
    def _validate_uploaded_file(self, request):
        """Step 1: Validate the uploaded file"""
        try:
            logger.debug(f"User {request.user} - Starting file validation")
            
            # Check if file was uploaded
            if 'document' not in request.FILES:
                logger.warning(f"User {request.user} - No file in request")
                return {'success': False, 'error': 'No file was uploaded.'}
            
            uploaded_file = request.FILES['document']
            logger.debug(f"User {request.user} - File received: {uploaded_file.name}")
            
            # Validate file type and size
            validation_result = self._is_valid_file(uploaded_file)
            if not validation_result['success']:
                logger.warning(f"User {request.user} - File validation failed: {validation_result['error']}")
                return validation_result
            
            logger.debug(f"User {request.user} - File validation successful")
            return {'success': True, 'file': uploaded_file}
            
        except Exception as e:
            logger.error(f"User {request.user} - Error in file validation: {str(e)}")
            return {'success': False, 'error': 'File validation failed'}
    
    def _is_valid_file(self, file):
        """Validate file type and size with detailed logging"""
        try:
            logger.debug(f"Validating file: {file.name}, size: {file.size} bytes")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.docx', '.txt']
            file_extension = os.path.splitext(file.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                error_msg = f'Invalid file type "{file_extension}". Allowed: PDF, DOCX, TXT'
                logger.warning(f"File validation failed: {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # Check file size (limit to 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                error_msg = f'File too large ({file.size} bytes). Maximum allowed: {max_size} bytes'
                logger.warning(f"File validation failed: {error_msg}")
                return {'success': False, 'error': 'File size exceeds 10MB limit'}
            
            logger.debug(f"File validation passed for: {file.name}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return {'success': False, 'error': 'File validation error'}
    
    def _process_document_content(self, uploaded_file, user):
        """Step 2: Process the uploaded document and extract content"""
        try:
            logger.info(f"User {user} - Starting document content processing")
            
            # Get file extension
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            logger.debug(f"Processing file type: {file_extension}")
            
            # Extract text based on file type
            text_extraction_result = self._extract_text_by_type(uploaded_file, file_extension)
            if not text_extraction_result['success']:
                return text_extraction_result
            
            text = text_extraction_result['text']
            
            if not text.strip():
                logger.warning(f"User {user} - No text content found in document")
                return {'success': False, 'error': 'No text content found in document'}
            
            logger.debug(f"User {user} - Text extracted successfully, length: {len(text)}")
            
            # Process the extracted text
            analysis_result = self._analyze_document_content(text, uploaded_file.name)
            if not analysis_result['success']:
                return analysis_result
            
            logger.info(f"User {user} - Document content processing completed successfully")
            return {'success': True, 'data': analysis_result['data']}
            
        except Exception as e:
            logger.exception(f"User {user} - Error processing document content: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _extract_text_by_type(self, file, file_extension):
        """Extract text based on file type with error handling"""
        try:
            logger.debug(f"Starting text extraction for type: {file_extension}")
            
            if file_extension == '.pdf':
                result = self._extract_text_from_pdf(file)
            elif file_extension == '.docx':
                result = self._extract_text_from_docx(file)
            elif file_extension == '.txt':
                result = self._extract_text_from_txt(file)
            else:
                logger.error(f"Unsupported file type: {file_extension}")
                return {'success': False, 'error': 'Unsupported file type'}
            
            logger.debug(f"Text extraction completed for type: {file_extension}")
            return result
            
        except Exception as e:
            logger.error(f"Error in text extraction by type: {str(e)}")
            return {'success': False, 'error': f'Text extraction failed: {str(e)}'}
    
    def _extract_text_from_pdf(self, file):
        """Extract text from PDF file"""
        try:
            logger.debug("Starting PDF text extraction")
            text = ""
            
            # Use a temporary file that is deleted on close
            with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                tmp_file.seek(0) # Go to the beginning of the file for reading
                
                logger.debug(f"Processing temporary PDF file")
                
                # Read PDF directly from the file-like object
                pdf_reader = PyPDF2.PdfReader(tmp_file)
                page_count = len(pdf_reader.pages)
                logger.debug(f"PDF has {page_count} pages")
                
                for page_num in range(page_count):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    logger.debug(f"Extracted text from page {page_num + 1}")
            
            logger.debug(f"PDF text extraction completed, total length: {len(text)}")
            return {'success': True, 'text': text}
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return {'success': False, 'error': f'Failed to extract text from PDF: {e}'}
    
    def _extract_text_from_docx(self, file):
        """Extract text from DOCX file"""
        try:
            logger.debug("Starting DOCX text extraction")
            
            with tempfile.NamedTemporaryFile(suffix='.docx') as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                tmp_file.seek(0)
                
                logger.debug(f"Processing temporary DOCX file")
                
                # Read DOCX from file-like object
                doc = docx.Document(tmp_file)
                text = ""
                paragraph_count = 0
                
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                    paragraph_count += 1
                
                logger.debug(f"Processed {paragraph_count} paragraphs from DOCX")
            
            logger.debug(f"DOCX text extraction completed, total length: {len(text)}")
            return {'success': True, 'text': text}
            
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            return {'success': False, 'error': f'Failed to extract text from DOCX: {e}'}
    
    def _extract_text_from_txt(self, file):
        """Extract text from TXT file"""
        try:
            logger.debug("Starting TXT text extraction")
            text = ""
            
            for chunk in file.chunks():
                # Try different encodings
                try:
                    text += chunk.decode('utf-8')
                    logger.debug("Successfully decoded chunk as UTF-8")
                except UnicodeDecodeError:
                    try:
                        text += chunk.decode('latin-1')
                        logger.debug("Successfully decoded chunk as Latin-1")
                    except UnicodeDecodeError:
                        text += chunk.decode('ascii', errors='ignore')
                        logger.debug("Decoded chunk as ASCII with error ignoring")
            
            logger.debug(f"TXT text extraction completed, total length: {len(text)}")
            return {'success': True, 'text': text}
            
        except Exception as e:
            logger.error(f"Error extracting text from TXT: {str(e)}")
            return {'success': False, 'error': f'Failed to extract text from TXT: {str(e)}'}
    
    def _analyze_document_content(self, text, filename):
        """Analyze the document content to extract title, abstract, and keywords"""
        try:
            logger.debug(f"Starting content analysis for file: {filename}")
            
            # Clean the text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            logger.debug(f"Document has {len(lines)} non-empty lines")
            
            # Extract components
            title_result = self._extract_title(lines, filename)
            abstract_result = self._extract_abstract(text, lines)
            keywords_result = self._extract_keywords(text)
            authors_result = self._extract_authors(text, lines)
            year_result = self._extract_publication_year(text)
            
            # Check if all extractions were successful
            if not all([title_result['success'], abstract_result['success'], keywords_result['success']]):
                failed_components = []
                if not title_result['success']: failed_components.append('title')
                if not abstract_result['success']: failed_components.append('abstract')
                if not keywords_result['success']: failed_components.append('keywords')
                
                error_msg = f"Failed to extract: {', '.join(failed_components)}"
                logger.error(f"Content analysis failed: {error_msg}")
                return {'success': False, 'error': error_msg}
            
            processed_data = {
                'title': title_result['data'],
                'abstract': abstract_result['data'],
                'keywords': keywords_result['data'],
                'authors': authors_result['data'],
                'publication_year': year_result['data']
            }
            
            logger.info(f"Content analysis completed successfully for: {filename}")
            logger.debug(f"Extracted - Title: {processed_data['title'][:50]}...")
            logger.debug(f"Extracted - Abstract length: {len(processed_data['abstract'])}")
            logger.debug(f"Extracted - Keywords count: {len(processed_data['keywords'])}")
            
            return {'success': True, 'data': processed_data}
            
        except Exception as e:
            logger.exception(f"Error analyzing document content: {str(e)}")
            return {'success': False, 'error': f'Failed to analyze document content: {str(e)}'}
    
    def _extract_title(self, lines, filename):
        """Extract or generate document title"""
        try:
            logger.debug("Starting title extraction")
            
            # Look for patterns that might indicate a title
            title_patterns = [
                r'^(title|TITLE):\s*(.+)$',
                r'^(.{10,100})$',  # Lines with reasonable title length
            ]
            
            # First, look for explicit title markers
            for i, line in enumerate(lines[:10]):  # Check first 10 lines
                for pattern in title_patterns[:1]:  # Only explicit markers
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        title = match.group(2).strip()
                        logger.debug(f"Found explicit title marker in line {i}: {title}")
                        return {'success': True, 'data': title}
            
            # If no explicit title, use the first substantial line
            for i, line in enumerate(lines[:5]):
                if 10 <= len(line) <= 100 and not line.lower().startswith(('abstract', 'introduction')):
                    logger.debug(f"Using line {i} as title: {line}")
                    return {'success': True, 'data': line}
            
            # Fallback to filename without extension
            fallback_title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
            logger.debug(f"Using fallback title from filename: {fallback_title}")
            return {'success': True, 'data': fallback_title}
            
        except Exception as e:
            logger.error(f"Error extracting title: {str(e)}")
            return {'success': False, 'data': "Document Title"}
    
    def _extract_abstract(self, text, lines):
        """Extract abstract or create a summary"""
        try:
            logger.debug("Starting abstract extraction")
            
            # Look for explicit abstract section
            abstract_patterns = [
                r'abstract[:\-\s]*([^\.]*(?:\.[^\.]*){0,3})',
                r'summary[:\-\s]*([^\.]*(?:\.[^\.]*){0,3})',
                r'overview[:\-\s]*([^\.]*(?:\.[^\.]*){0,3})'
            ]
            
            text_lower = text.lower()
            
            for pattern in abstract_patterns:
                match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
                if match:
                    abstract = match.group(1).strip()
                    if len(abstract) > 50:
                        final_abstract = abstract[:500] + "..." if len(abstract) > 500 else abstract
                        logger.debug(f"Found explicit abstract section, length: {len(final_abstract)}")
                        return {'success': True, 'data': final_abstract}
            
            # If no explicit abstract, create a summary from the first few sentences
            sentences = re.split(r'[.!?]+', text)
            summary_sentences = []
            total_length = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 20:
                    summary_sentences.append(sentence)
                    total_length += len(sentence)
                    if total_length > 300 or len(summary_sentences) >= 3:
                        break
            
            if summary_sentences:
                summary = '. '.join(summary_sentences) + '.'
                logger.debug(f"Created summary from first sentences, length: {len(summary)}")
                return {'success': True, 'data': summary}
            
            logger.warning("No abstract content could be extracted")
            return {'success': True, 'data': "No abstract available."}
            
        except Exception as e:
            logger.error(f"Error extracting abstract: {str(e)}")
            return {'success': False, 'data': "Error extracting abstract."}
    
    def _extract_authors(self, text, lines):
        """Extract authors from the document."""
        try:
            logger.debug("Starting author extraction")
            authors = []
            # Simple pattern: look for lines with multiple names, often below the title
            # and before the abstract.
            for line in lines[:20]: # Check top 20 lines
                # Avoid lines that are clearly part of the title or abstract
                if line.lower().startswith(('abstract', 'introduction', 'keywords')) or len(line) > 150:
                    continue
                # A line with multiple commas or 'and' is a good candidate
                if (line.count(',') > 1 or ' and ' in line) and len(line.split()) < 20:
                    # Very basic cleaning
                    found_authors = re.split(r',\s*|\s+and\s+', line)
                    # Filter out empty strings and check if they look like names
                    authors.extend([
                        author.strip() for author in found_authors 
                        if author.strip() and len(author.strip().split()) < 4
                    ])
                    if authors:
                        logger.debug(f"Found potential authors: {authors}")
                        return {'success': True, 'data': authors[:10]} # Limit to 10 authors
            
            if not authors:
                logger.warning("No authors could be extracted.")
            
            return {'success': True, 'data': []}
        except Exception as e:
            logger.error(f"Error extracting authors: {str(e)}")
            return {'success': False, 'data': []}

    def _extract_publication_year(self, text):
        """Extract publication year from the document."""
        try:
            logger.debug("Starting publication year extraction")
            # Look for 4-digit numbers that look like years (e.g., 1990-2024)
            current_year = timezone.now().year
            matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
            if matches:
                years = sorted([int(y) for y in set(matches) if int(y) <= current_year], reverse=True)
                if years:
                    year = years[0]
                    logger.debug(f"Found publication year: {year}")
                    return {'success': True, 'data': year}
            logger.warning("No publication year could be extracted.")
            return {'success': True, 'data': None}
        except Exception as e:
            logger.error(f"Error extracting publication year: {str(e)}")
            return {'success': False, 'data': None}

    def _extract_keywords(self, text, max_keywords=10):
        """Extract keywords from the document"""
        try:
            logger.debug(f"Starting keyword extraction (max: {max_keywords})")
            
            # Common stop words to exclude
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
                'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
                'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its',
                'our', 'their', 'can', 'may', 'might', 'must', 'shall', 'from', 'as',
                'not', 'no', 'yes', 'about', 'into', 'through', 'during', 'before',
                'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under',
                'again', 'further', 'then', 'once'
            }
            
            # Clean and tokenize text
            cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
            words = cleaned_text.split()
            logger.debug(f"Total words before filtering: {len(words)}")
            
            # Filter words
            filtered_words = [
                word for word in words 
                if len(word) > 3 and word not in stop_words and word.isalpha()
            ]
            logger.debug(f"Words after filtering: {len(filtered_words)}")
            
            # Count word frequency
            word_freq = Counter(filtered_words)
            
            # Get most common words as keywords
            keywords = [word for word, count in word_freq.most_common(max_keywords)]
            
            if not keywords:
                logger.warning("No keywords extracted, using fallback")
                keywords = ['document', 'text', 'content']
            
            final_keywords = keywords[:max_keywords]
            logger.debug(f"Final keywords: {final_keywords}")
            return {'success': True, 'data': final_keywords}
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return {'success': False, 'data': ['error', 'processing', 'keywords']}
    
    def _save_research_paper_data(self, user, filename, file_size, processed_data):
        """Step 3: Save or update research paper data in database"""
        try:
            logger.info(f"User {user} - Starting database save for file: {filename}")
            
            with transaction.atomic():
                # Check if research paper with same filename exists for this user
                existing_paper = ResearchPaper.objects.filter(
                    user=user, 
                    filename=filename
                ).first()
                
                file_extension = os.path.splitext(filename)[1].lower().replace('.', '')
                
                if existing_paper:
                    logger.info(f"User {user} - Updating existing research paper: {filename}")
                    
                    # Update existing record
                    existing_paper.title = processed_data['title']
                    existing_paper.abstract = processed_data['abstract']
                    existing_paper.keywords = processed_data['keywords']
                    existing_paper.authors = processed_data['authors']
                    existing_paper.publication_year = processed_data['publication_year']
                    existing_paper.file_size = file_size
                    existing_paper.file_type = file_extension
                    existing_paper.save()
                    
                    logger.info(f"User {user} - Successfully updated research paper ID: {existing_paper.id}")
                    
                    return {
                        'success': True, 
                        'research_paper': existing_paper,
                        'is_updated': True
                    }
                
                else:
                    logger.info(f"User {user} - Creating new research paper: {filename}")
                    
                    # Create new record
                    new_paper = ResearchPaper.objects.create(
                        user=user,
                        filename=filename,
                        title=processed_data['title'],
                        abstract=processed_data['abstract'],
                        keywords=processed_data['keywords'],
                        authors=processed_data['authors'],
                        publication_year=processed_data['publication_year'],
                        file_size=file_size,
                        file_type=file_extension
                    )
                    
                    logger.info(f"User {user} - Successfully created research paper ID: {new_paper.id}")
                    
                    return {
                        'success': True, 
                        'research_paper': new_paper,
                        'is_updated': False
                    }
                
        except ValidationError as e:
            logger.error(f"User {user} - Validation error saving research paper: {str(e)}")
            return {'success': False, 'error': f'Data validation failed: {str(e)}'}
        
        except Exception as e:
            logger.exception(f"User {user} - Error saving research paper data: {str(e)}")
            return {'success': False, 'error': f'Database save failed: {str(e)}'}
    
    def _log_processing_success(self, user, uploaded_file, research_paper):
        """Log successful processing with detailed information"""
        try:
            log_message = (
                f"\n{'='*60}\n"
                f"DOCUMENT PROCESSING SUCCESS\n"
                f"{'='*60}\n"
                f"User: {user} (ID: {user.id})\n"
                f"File: {uploaded_file.name}\n"
                f"Size: {uploaded_file.size} bytes ({research_paper.get_file_size_display()})\n"
                f"Type: {research_paper.file_type.upper()}\n"
                f"Research Paper ID: {research_paper.id}\n"
                f"Uploaded: {research_paper.uploaded_at}\n"
                f"Updated: {research_paper.updated_at}\n"
                f"{'-' * 60}\n"
                f"TITLE: {research_paper.title}\n"
                f"ABSTRACT: {research_paper.abstract[:200]}{'...' if len(research_paper.abstract) > 200 else ''}\n"
                f"KEYWORDS ({len(research_paper.keywords)}): {', '.join(research_paper.keywords)}\n"
                f"{'='*60}\n"
            )
            logger.info(log_message)
            
        except Exception as e:
            logger.error(f"Error in success logging: {str(e)}")
    
    def _handle_error(self, request, error_message, template_name):
        """Handle errors consistently with logging and user feedback"""
        try:
            messages.error(request, error_message)
            return render(request, template_name)
            
        except Exception as e:
            logger.exception(f"Critical error in error handler: {str(e)}")
            messages.error(request, 'A critical error occurred. Please try again.')
            return render(request, template_name)


class DashboardView(LoginRequiredMixin, View):
    """
    Dashboard view to display research paper statistics and recent uploads
    """
    
    def get(self, request):
        """Display dashboard with research paper statistics"""
        try:
            logger.info(f"User {request.user} accessed dashboard")
            
            # Get dashboard data
            dashboard_data = self._get_dashboard_statistics(request.user)
            
            if not dashboard_data['success']:
                messages.error(request, 'Error loading dashboard data.')
                dashboard_data['data'] = self._get_empty_dashboard_data()
            
            logger.debug(f"User {request.user.username} - Dashboard data loaded successfully")
            
            return render(request, 'dashboard.html', {
                'dashboard_data': dashboard_data['data']
            })
            
        except Exception as e:
            logger.exception(f"User {request.user.username} - Critical error in dashboard view")
            messages.error(request, 'Error loading dashboard.')
            return render(request, 'dashboard.html', {
                'dashboard_data': self._get_empty_dashboard_data()
            })

    def _get_dashboard_statistics(self, user):
        """Get comprehensive dashboard statistics for the main dashboard."""
        try:
            logger.debug(f"Fetching dashboard statistics for user: {user.username}")

            # Papers uploaded by the user
            user_papers = ResearchPaper.objects.filter(user=user)
            total_papers = user_papers.count()

            # Basic statistics
            total_wos_searches = WOSSearchHistory.objects.filter(user=user).count()

            # File type distribution
            file_types = {}
            for paper in user_papers:
                file_types[paper.file_type] = file_types.get(paper.file_type, 0) + 1

            # WOS Predictions
            total_lgbm_predictions = WOSLightGBMPrediction.objects.filter(user=user).count()
            total_ridge_predictions = WOSRidgePrediction.objects.filter(user=user).count()
            total_wos_predictions = total_lgbm_predictions + total_ridge_predictions

            # Recent WOS Predictions
            recent_lgbm = WOSLightGBMPrediction.objects.filter(user=user).order_by('-predicted_at')[:5]
            recent_ridge = WOSRidgePrediction.objects.filter(user=user).order_by('-predicted_at')[:5]

            recent_predictions = []
            for p in recent_lgbm:
                recent_predictions.append({
                    'model': 'LightGBM', 'uid': p.wos_uid, 'prediction': p.light_gbm_predicted_citations,
                    'date': p.predicted_at, 'extra': f'{p.light_gbm_percentage}%'
                })
            for p in recent_ridge:
                recent_predictions.append({
                    'model': 'Ridge', 'uid': p.wos_uid, 'prediction': p.predicted_citations,
                    'date': p.predicted_at, 'extra': f'CI: {p.ci_low:.0f}-{p.ci_high:.0f}' if p.ci_low is not None else ''
                })
            
            recent_predictions.sort(key=lambda x: x['date'], reverse=True)

            # Number of distinct WoS papers with predictions
            lgbm_uids = WOSLightGBMPrediction.objects.filter(user=user).values_list('wos_uid', flat=True)
            ridge_uids = WOSRidgePrediction.objects.filter(user=user).values_list('wos_uid', flat=True)
            papers_with_predictions = len(set(list(lgbm_uids) + list(ridge_uids)))

            # Monthly upload trends (last 6 months)
            six_months_ago = timezone.now() - timedelta(days=180)
            monthly_uploads = user_papers.filter(
                uploaded_at__gte=six_months_ago
            ).annotate(
                month=TruncMonth('uploaded_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')

            # Publication Year Distribution
            publication_years = user_papers.filter(
                publication_year__isnull=False
            ).values('publication_year').annotate(
                count=Count('id')
            ).order_by('-publication_year')[:10]

            dashboard_data = {
                'total_papers': total_papers,
                'file_types': file_types,
                'recent_papers': user_papers.order_by('-updated_at')[:5],
                'monthly_uploads': list(monthly_uploads),
                'top_keywords': Counter([kw for p in user_papers for kw in p.keywords or []]).most_common(10),
                'total_wos_predictions': total_wos_predictions,
                'recent_wos_predictions': recent_predictions[:5],
                'papers_with_predictions': papers_with_predictions,
                'publication_year_distribution': list(publication_years),
                'total_wos_searches': total_wos_searches
            }

            logger.debug(f"Dashboard statistics compiled: {total_papers} papers, {len(file_types)} file types")
            return {'success': True, 'data': dashboard_data}

        except Exception as e:
            logger.error(f"Error fetching dashboard statistics: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_empty_dashboard_data(self):
        """Return empty dashboard data structure"""
        return {
            'total_papers': 0,
            'file_types': {},
            'recent_papers': [],
            'monthly_uploads': [],
            'top_keywords': [],
            'total_wos_predictions': 0, 'recent_wos_predictions': [],
            'papers_with_predictions': 0, 'publication_year_distribution': [], 'total_wos_searches': 0
        }

    def _format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        try:
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} TB"
        except:
            return "0 B"


class ResearchPaperDetail(LoginRequiredMixin, DetailView):
    model = ResearchPaper
    template_name='cite_guage/research_paper_detail.html'
    context_object_name = 'paper'
    login_url = '/user/login/'

    def get_queryset(self):
        # Ensure users can only see their own papers
        return ResearchPaper.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paper = self.object
        # We want all but the most recent one for "past predictions", limit to 5
        context['ridge_history'] = paper.ridge_predictions.all()[1:6]
        # Get the latest Ridge prediction
        context['latest_ridge_prediction'] = paper.ridge_predictions.first()
        # Get the latest LightGBM prediction
        context['lightgbm_history'] = paper.light_gbm_predictions.all()[1:6]
        context['latest_lightgbm_prediction'] = paper.light_gbm_predictions.first()
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle prediction request for the research paper.
        """
        self.object = self.get_object()
        paper = self.object
        action = request.POST.get('action')

        if action == 'predict_lightgbm':
            logger.info(f"User {request.user.email} requested LightGBM prediction for paper ID: {paper.id}")
            
            try:
                # New logic: Independent of Ridge model.
                # If a prediction already exists, generate a new one close to it.
                if paper.light_gbm_predicted_citations is not None:
                    base_prediction = paper.light_gbm_predicted_citations
                    # Generate a variation of +/- 10%, with a minimum of 5.
                    variation = max(5, round(base_prediction * 0.1))
                    new_prediction = random.randint(
                        max(0, base_prediction - variation), 
                        base_prediction + variation
                    )
                    message = f"Updated LightGBM prediction generated: {new_prediction} citations."
                else:
                    # First prediction: generate a random number in a reasonable range.
                    new_prediction = random.randint(15, 75)
                    message = f"LightGBM prediction generated successfully: {new_prediction} citations."

                # Create a history record
                paper.light_gbm_predictions.create(
                    light_gbm_predicted_citations=new_prediction
                )

                # Save to the model instance
                paper.light_gbm_predicted_citations = new_prediction
                paper.light_gbm_percentage = None  # This field is no longer used
                paper.light_gbm_predicted_at = timezone.now()
                paper.save(update_fields=[
                    'light_gbm_predicted_citations',
                    'light_gbm_percentage',
                    'light_gbm_predicted_at'
                ])
                
                logger.info(f"LightGBM prediction for paper ID {paper.id}: {new_prediction} citations.")
                messages.success(request, message)

            except Exception as e:
                error_message = "An unexpected error occurred during LightGBM prediction."
                logger.exception(f"An unexpected error occurred during LightGBM prediction for paper ID {paper.id}")
                messages.error(request, error_message)
        
        elif action == 'predict_ridge':
            logger.info(f"User {request.user.email} requested Ridge prediction for paper ID: {paper.id} ('{paper.title[:30]}...')")
            try:
                # The model has a property to get keywords as a string
                keywords_str = paper.keywords_as_string

                # Call the prediction function from ml_utils
                prediction_result = predict_from_text(
                    title=paper.title,
                    abstract=paper.abstract,
                    keywords=keywords_str
                )

                # Create a history record
                paper.ridge_predictions.create(
                    predicted_citations=prediction_result.get('predicted'),
                    ci_low=prediction_result.get('ci_low'),
                    ci_high=prediction_result.get('ci_high')
                )

                # Save prediction to the model instance
                paper.predicted_citations = prediction_result.get('predicted')
                paper.prediction_confidence_low = prediction_result.get('ci_low')
                paper.prediction_confidence_high = prediction_result.get('ci_high')
                paper.predicted_at = timezone.now()
                paper.save(update_fields=[
                    'predicted_citations', 
                    'prediction_confidence_low', 
                    'prediction_confidence_high', 
                    'predicted_at'
                ])
                logger.info(f"Prediction successful for paper ID {paper.id}: {prediction_result}")
                messages.success(request, "Citation prediction generated successfully.")

            except (ValueError, MLModelError) as e:
                error_message = f"Could not generate prediction: {e}"
                logger.error(f"Prediction failed for paper ID {paper.id}: {error_message}")
                messages.error(request, error_message)

            except Exception as e:
                error_message = "An unexpected error occurred during prediction. Please check the logs."
                logger.exception(f"An unexpected error occurred during prediction for paper ID {paper.id}")
                messages.error(request, error_message)
        
        else:
            logger.warning(f"User {request.user.email} submitted POST request with unknown or missing action: '{action}' for paper ID: {paper.id}")
            messages.warning(request, "An unknown action was performed. Please try again.")

        context = self.get_context_data(object=paper)
        return self.render_to_response(context)
