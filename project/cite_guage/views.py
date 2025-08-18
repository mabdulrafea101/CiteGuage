from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
import PyPDF2
import docx
import re
from collections import Counter
import os
import logging
import tempfile

from django.views import View
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'cite_guage/dashboard.html'
    login_url = '/user/login/'  # Redirect to login if not authenticated





# Set up logging for debugging
logger = logging.getLogger(__name__)

class DocumentProcessorView(LoginRequiredMixin, View):
    """
    Class-based view for handling document upload and processing.
    Requires user authentication.
    """
    
    def get(self, request):
        """Render the upload form"""
        return render(request, 'cite_guage/upload_documents.html')
    
    def post(self, request):
        """Handle document upload and processing"""
        try:
            # Check if file was uploaded
            if 'document' not in request.FILES:
                messages.error(request, 'No file was uploaded.')
                logger.error(f"User {request.user.username} - No file in request")
                return render(request, 'cite_guage/upload_documents.html')
            
            uploaded_file = request.FILES['document']
            
            # Validate file
            if not self.is_valid_file(uploaded_file):
                messages.error(request, 'Invalid file type. Please upload PDF, DOCX, or TXT files only.')
                logger.error(f"User {request.user.username} - Invalid file type: {uploaded_file.name}")
                return render(request, 'cite_guage/upload_documents.html')
            
            # Process the document
            result = self.process_document(uploaded_file, request.user)
            
            if result['success']:
                logger.info(f"User {request.user.username} - Document processed successfully: {uploaded_file.name}")
                
                # Print results to console for debugging
                print("\n" + "="*50)
                print(f"DOCUMENT PROCESSING RESULTS")
                print(f"User: {request.user.username}")
                print(f"File: {uploaded_file.name}")
                print(f"Size: {uploaded_file.size} bytes")
                print("="*50)
                print(f"TITLE: {result['data']['title']}")
                print(f"ABSTRACT: {result['data']['abstract']}")
                print(f"KEYWORDS: {', '.join(result['data']['keywords'])}")
                print("="*50 + "\n")
                
                # Add success message and pass data to template
                messages.success(request, 'Document processed successfully!')
                context = {
                    'result': result['data'],
                    'filename': uploaded_file.name
                }
                return render(request, 'cite_guage/document_results.html', context)
            
            else:
                messages.error(request, f'Error processing document: {result["error"]}')
                logger.error(f"User {request.user.username} - Processing error: {result['error']}")
                return render(request, 'cite_guage/upload_documents.html')
                
        except Exception as e:
            logger.exception(f"User {request.user.username} - Unexpected error in document processing")
            messages.error(request, 'An unexpected error occurred while processing your document.')
            print(f"CRITICAL ERROR: {str(e)}")
            return render(request, 'cite_guage/upload_documents.html')
    
    def is_valid_file(self, file):
        """Validate file type and size"""
        try:
            # Check file extension
            allowed_extensions = ['.pdf', '.docx', '.txt']
            file_extension = os.path.splitext(file.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                return False
            
            # Check file size (limit to 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                logger.warning(f"File too large: {file.size} bytes")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return False
    
    def process_document(self, uploaded_file, user):
        """
        Main function to process the uploaded document and extract:
        - Title
        - Abstract/Description
        - Keywords
        """
        try:
            # Get file extension
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            # Extract text based on file type
            if file_extension == '.pdf':
                text = self.extract_text_from_pdf(uploaded_file)
            elif file_extension == '.docx':
                text = self.extract_text_from_docx(uploaded_file)
            elif file_extension == '.txt':
                text = self.extract_text_from_txt(uploaded_file)
            else:
                return {'success': False, 'error': 'Unsupported file type'}
            
            if not text.strip():
                return {'success': False, 'error': 'No text content found in document'}
            
            # Process the extracted text
            processed_data = self.analyze_document_content(text, uploaded_file.name)
            
            logger.info(f"Successfully processed document for user {user.username}")
            
            return {
                'success': True,
                'data': processed_data
            }
            
        except Exception as e:
            logger.exception(f"Error processing document: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def extract_text_from_pdf(self, file):
        """Extract text from PDF file"""
        try:
            text = ""
            # Create a temporary file to work with
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                tmp_file.flush()
                
                # Read PDF
                with open(tmp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text += page.extract_text() + "\n"
                
                # Clean up temp file
                os.unlink(tmp_file.name)
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_text_from_docx(self, file):
        """Extract text from DOCX file"""
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                tmp_file.flush()
                
                # Read DOCX
                doc = docx.Document(tmp_file.name)
                text = ""
                
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                
                # Clean up temp file
                os.unlink(tmp_file.name)
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    def extract_text_from_txt(self, file):
        """Extract text from TXT file"""
        try:
            text = ""
            for chunk in file.chunks():
                # Try different encodings
                try:
                    text += chunk.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        text += chunk.decode('latin-1')
                    except UnicodeDecodeError:
                        text += chunk.decode('ascii', errors='ignore')
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from TXT: {str(e)}")
            raise Exception(f"Failed to extract text from TXT: {str(e)}")
    
    def analyze_document_content(self, text, filename):
        """
        Analyze the document content to extract title, abstract, and keywords
        """
        try:
            # Clean the text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Extract title
            title = self.extract_title(lines, filename)
            
            # Extract abstract/description
            abstract = self.extract_abstract(text, lines)
            
            # Extract keywords
            keywords = self.extract_keywords(text)
            
            return {
                'title': title,
                'abstract': abstract,
                'keywords': keywords
            }
            
        except Exception as e:
            logger.error(f"Error analyzing document content: {str(e)}")
            raise Exception(f"Failed to analyze document content: {str(e)}")
    
    def extract_title(self, lines, filename):
        """Extract or generate document title"""
        try:
            # Look for patterns that might indicate a title
            title_patterns = [
                r'^(title|TITLE):\s*(.+)$',
                r'^(.{10,100})$',  # Lines with reasonable title length
            ]
            
            # First, look for explicit title markers
            for line in lines[:10]:  # Check first 10 lines
                for pattern in title_patterns[:1]:  # Only explicit markers
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        return match.group(2).strip()
            
            # If no explicit title, use the first substantial line
            for line in lines[:5]:
                if 10 <= len(line) <= 100 and not line.lower().startswith(('abstract', 'introduction')):
                    return line
            
            # Fallback to filename without extension
            return os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
            
        except Exception as e:
            logger.error(f"Error extracting title: {str(e)}")
            return "Document Title"
    
    def extract_abstract(self, text, lines):
        """Extract abstract or create a summary"""
        try:
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
                        return abstract[:500] + "..." if len(abstract) > 500 else abstract
            
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
                return '. '.join(summary_sentences) + '.'
            
            return "No abstract available."
            
        except Exception as e:
            logger.error(f"Error extracting abstract: {str(e)}")
            return "Error extracting abstract."
    
    def extract_keywords(self, text, max_keywords=10):
        """Extract keywords from the document"""
        try:
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
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            words = text.split()
            
            # Filter words
            filtered_words = [
                word for word in words 
                if len(word) > 3 and word not in stop_words and word.isalpha()
            ]
            
            # Count word frequency
            word_freq = Counter(filtered_words)
            
            # Get most common words as keywords
            keywords = [word for word, count in word_freq.most_common(max_keywords)]
            
            return keywords[:max_keywords] if keywords else ['document', 'text', 'content']
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return ['error', 'processing', 'keywords']


# forms.py (optional - for form validation)
from django import forms

class DocumentUploadForm(forms.Form):
    document = forms.FileField(
        widget=forms.FileInput(attrs={
            'accept': '.pdf,.docx,.txt',
            'class': 'form-control'
        }),
        help_text='Upload PDF, DOCX, or TXT files (max 10MB)'
    )



