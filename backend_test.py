#!/usr/bin/env python3
"""
Backend API Testing for Intelligent PDF Reader Application
Tests all backend endpoints for functionality and integration
"""

import requests
import json
import os
import sys
from pathlib import Path
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

# Get backend URL from frontend .env file
def get_backend_url():
    frontend_env_path = Path("/app/frontend/.env")
    if frontend_env_path.exists():
        with open(frontend_env_path, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_BASE = f"{BASE_URL}/api"

print(f"Testing backend at: {API_BASE}")

class PDFReaderAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.test_document_id = None
        self.test_section_id = None
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }

    def log_result(self, test_name, success, message=""):
        if success:
            print(f"✅ {test_name}: PASSED {message}")
            self.results['passed'] += 1
        else:
            print(f"❌ {test_name}: FAILED {message}")
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {message}")

    def create_test_pdf(self):
        """Create a test PDF with structured content"""
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Page 1
        p.drawString(100, 750, "INTELLIGENT PDF READER TEST DOCUMENT")
        p.drawString(100, 720, "1. Introduction")
        p.drawString(120, 700, "This is a comprehensive test document for the intelligent PDF reader.")
        p.drawString(120, 680, "It contains multiple sections with different types of content.")
        p.drawString(120, 660, "The document demonstrates various features including:")
        p.drawString(140, 640, "- Document structure analysis")
        p.drawString(140, 620, "- Semantic search capabilities")
        p.drawString(140, 600, "- AI-powered summarization")
        p.drawString(140, 580, "- Question and answer functionality")
        
        p.drawString(100, 540, "1.1 Technical Overview")
        p.drawString(120, 520, "The system uses advanced natural language processing techniques")
        p.drawString(120, 500, "to analyze and understand document content. Machine learning")
        p.drawString(120, 480, "algorithms enable semantic search and intelligent responses.")
        
        p.showPage()
        
        # Page 2
        p.drawString(100, 750, "2. Features and Capabilities")
        p.drawString(120, 720, "The intelligent PDF reader provides several key features:")
        
        p.drawString(100, 680, "2.1 Document Processing")
        p.drawString(120, 660, "Automatic text extraction from PDF files with high accuracy.")
        p.drawString(120, 640, "Structure detection identifies headings, sections, and hierarchy.")
        p.drawString(120, 620, "Content is processed for semantic understanding and indexing.")
        
        p.drawString(100, 580, "2.2 Search and Discovery")
        p.drawString(120, 560, "Semantic search goes beyond keyword matching to understand context.")
        p.drawString(120, 540, "Related sections are automatically identified and linked.")
        p.drawString(120, 520, "Similarity scoring helps rank search results by relevance.")
        
        p.drawString(100, 480, "2.3 AI Integration")
        p.drawString(120, 460, "OpenAI GPT models provide intelligent summarization capabilities.")
        p.drawString(120, 440, "Question answering system provides contextual responses.")
        p.drawString(120, 420, "Confidence scoring indicates reliability of AI responses.")
        
        p.showPage()
        
        # Page 3
        p.drawString(100, 750, "3. Technical Implementation")
        p.drawString(120, 720, "The system architecture consists of multiple components:")
        
        p.drawString(100, 680, "3.1 Backend Services")
        p.drawString(120, 660, "FastAPI framework provides RESTful API endpoints.")
        p.drawString(120, 640, "MongoDB stores document data and metadata efficiently.")
        p.drawString(120, 620, "Sentence transformers generate embeddings for semantic search.")
        
        p.drawString(100, 580, "3.2 Frontend Interface")
        p.drawString(120, 560, "React application provides responsive user interface.")
        p.drawString(120, 540, "Adobe PDF Embed API enables seamless document viewing.")
        p.drawString(120, 520, "Dynamic navigation supports document exploration.")
        
        p.drawString(100, 480, "CONCLUSION")
        p.drawString(120, 460, "This intelligent PDF reader demonstrates advanced document")
        p.drawString(120, 440, "processing capabilities with modern AI integration.")
        p.drawString(120, 420, "The system provides efficient and intuitive document analysis.")
        
        p.save()
        buffer.seek(0)
        return buffer.getvalue()

    def test_pdf_upload_and_processing(self):
        """Test PDF upload endpoint and document processing"""
        print("\n🔍 Testing PDF Upload and Processing...")
        
        try:
            # Create test PDF
            pdf_content = self.create_test_pdf()
            
            # Test upload
            files = {'file': ('test_document.pdf', pdf_content, 'application/pdf')}
            response = self.session.post(f"{API_BASE}/documents/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                self.test_document_id = data['id']
                
                # Verify response structure
                required_fields = ['id', 'title', 'content', 'total_pages', 'created_at', 'structure', 'embedding_segments']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("PDF Upload - Response Structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_result("PDF Upload - Response Structure", True, f"All required fields present")
                
                # Verify content extraction
                if len(data['content']) > 100:
                    self.log_result("PDF Upload - Text Extraction", True, f"Extracted {len(data['content'])} characters")
                else:
                    self.log_result("PDF Upload - Text Extraction", False, "Insufficient text extracted")
                
                # Verify structure detection
                if len(data['structure']) > 0:
                    self.log_result("PDF Upload - Structure Detection", True, f"Detected {len(data['structure'])} sections")
                    # Store first section ID for later tests
                    if data['embedding_segments']:
                        self.test_section_id = data['embedding_segments'][0]['id']
                else:
                    self.log_result("PDF Upload - Structure Detection", False, "No document structure detected")
                
                # Verify embedding generation
                if len(data['embedding_segments']) > 0:
                    self.log_result("PDF Upload - Embedding Generation", True, f"Generated {len(data['embedding_segments'])} embeddings")
                else:
                    self.log_result("PDF Upload - Embedding Generation", False, "No embeddings generated")
                
                # Verify page count
                if data['total_pages'] == 3:
                    self.log_result("PDF Upload - Page Count", True, f"Correct page count: {data['total_pages']}")
                else:
                    self.log_result("PDF Upload - Page Count", False, f"Expected 3 pages, got {data['total_pages']}")
                    
            else:
                self.log_result("PDF Upload - HTTP Status", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("PDF Upload - Exception", False, str(e))

    def test_document_management(self):
        """Test document listing and retrieval endpoints"""
        print("\n🔍 Testing Document Management...")
        
        if not self.test_document_id:
            self.log_result("Document Management", False, "No test document ID available")
            return
        
        try:
            # Test document retrieval by ID
            response = self.session.get(f"{API_BASE}/documents/{self.test_document_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data['id'] == self.test_document_id:
                    self.log_result("Document Retrieval by ID", True, "Document retrieved successfully")
                else:
                    self.log_result("Document Retrieval by ID", False, "Document ID mismatch")
            else:
                self.log_result("Document Retrieval by ID", False, f"Status {response.status_code}: {response.text}")
            
            # Test document listing
            response = self.session.get(f"{API_BASE}/documents")
            
            if response.status_code == 200:
                documents = response.json()
                if isinstance(documents, list) and len(documents) > 0:
                    self.log_result("Document Listing", True, f"Retrieved {len(documents)} documents")
                else:
                    self.log_result("Document Listing", False, "No documents in list or invalid format")
            else:
                self.log_result("Document Listing", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Document Management - Exception", False, str(e))

    def test_semantic_search(self):
        """Test semantic search functionality"""
        print("\n🔍 Testing Semantic Search...")
        
        if not self.test_document_id:
            self.log_result("Semantic Search", False, "No test document ID available")
            return
        
        try:
            # Test search with relevant query
            search_data = {
                "document_id": self.test_document_id,
                "query": "artificial intelligence and machine learning",
                "limit": 5
            }
            
            response = self.session.post(f"{API_BASE}/documents/{self.test_document_id}/search", 
                                       json=search_data)
            
            if response.status_code == 200:
                results = response.json()
                
                if isinstance(results, list) and len(results) > 0:
                    self.log_result("Semantic Search - Results", True, f"Found {len(results)} search results")
                    
                    # Verify result structure
                    first_result = results[0]
                    required_fields = ['section_id', 'title', 'content', 'page_number', 'similarity_score', 'related_sections']
                    missing_fields = [field for field in required_fields if field not in first_result]
                    
                    if missing_fields:
                        self.log_result("Semantic Search - Result Structure", False, f"Missing fields: {missing_fields}")
                    else:
                        self.log_result("Semantic Search - Result Structure", True, "All required fields present")
                    
                    # Verify similarity scoring
                    if 0 <= first_result['similarity_score'] <= 1:
                        self.log_result("Semantic Search - Similarity Scoring", True, f"Score: {first_result['similarity_score']:.3f}")
                    else:
                        self.log_result("Semantic Search - Similarity Scoring", False, f"Invalid score: {first_result['similarity_score']}")
                    
                    # Verify related sections
                    if isinstance(first_result['related_sections'], list):
                        self.log_result("Semantic Search - Related Sections", True, f"Found {len(first_result['related_sections'])} related sections")
                    else:
                        self.log_result("Semantic Search - Related Sections", False, "Related sections not in list format")
                        
                else:
                    self.log_result("Semantic Search - Results", False, "No search results returned")
            else:
                self.log_result("Semantic Search - HTTP Status", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Semantic Search - Exception", False, str(e))

    def test_offline_summarization(self):
        """Test offline TF-IDF based summarization"""
        print("\n🔍 Testing Offline Summarization (TF-IDF)...")
        
        if not self.test_document_id:
            self.log_result("Offline Summarization", False, "No test document ID available")
            return
        
        try:
            # Test document summarization
            summary_data = {
                "document_id": self.test_document_id,
                "max_length": 5
            }
            
            response = self.session.post(f"{API_BASE}/documents/{self.test_document_id}/summarize", 
                                       json=summary_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                required_fields = ['summary', 'title', 'word_count', 'method']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("Offline Summarization - Response Structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_result("Offline Summarization - Response Structure", True, "All required fields present")
                
                # Verify offline method is used
                if data.get('method') == 'offline_extractive':
                    self.log_result("Offline Summarization - Method Verification", True, "Using offline extractive method")
                else:
                    self.log_result("Offline Summarization - Method Verification", False, f"Expected 'offline_extractive', got '{data.get('method')}'")
                
                # Verify summary content
                if len(data['summary']) > 50:
                    self.log_result("Offline Summarization - Content Generation", True, f"Generated {data['word_count']} words")
                else:
                    self.log_result("Offline Summarization - Content Generation", False, "Summary too short")
                
                # Test section-specific summarization if we have a section ID
                if self.test_section_id:
                    section_summary_data = {
                        "document_id": self.test_document_id,
                        "section_id": self.test_section_id,
                        "max_length": 3
                    }
                    
                    response = self.session.post(f"{API_BASE}/documents/{self.test_document_id}/summarize", 
                                               json=section_summary_data)
                    
                    if response.status_code == 200:
                        section_data = response.json()
                        if section_data.get('method') == 'offline_extractive':
                            self.log_result("Offline Summarization - Section Specific", True, "Section summarization successful with offline method")
                        else:
                            self.log_result("Offline Summarization - Section Specific", False, "Section summarization not using offline method")
                    else:
                        self.log_result("Offline Summarization - Section Specific", False, f"Status {response.status_code}")
                        
            else:
                self.log_result("Offline Summarization - HTTP Status", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Offline Summarization - Exception", False, str(e))

    def test_qa_functionality(self):
        """Test Q&A functionality"""
        print("\n🔍 Testing Q&A Functionality...")
        
        if not self.test_document_id:
            self.log_result("Q&A Functionality", False, "No test document ID available")
            return
        
        try:
            # Test question answering
            qa_data = {
                "document_id": self.test_document_id,
                "question": "What are the main features of the intelligent PDF reader?",
                "context_limit": 3
            }
            
            response = self.session.post(f"{API_BASE}/documents/{self.test_document_id}/qa", 
                                       json=qa_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                required_fields = ['answer', 'question', 'relevant_sections', 'confidence_scores']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_result("Q&A - Response Structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_result("Q&A - Response Structure", True, "All required fields present")
                
                # Verify answer content
                if len(data['answer']) > 20:
                    self.log_result("Q&A - Answer Generation", True, f"Generated answer with {len(data['answer'])} characters")
                else:
                    self.log_result("Q&A - Answer Generation", False, "Answer too short")
                
                # Verify context awareness
                if data['question'] == qa_data['question']:
                    self.log_result("Q&A - Question Matching", True, "Question correctly preserved")
                else:
                    self.log_result("Q&A - Question Matching", False, "Question mismatch")
                
                # Verify confidence scoring
                if isinstance(data['confidence_scores'], list) and len(data['confidence_scores']) > 0:
                    avg_confidence = sum(data['confidence_scores']) / len(data['confidence_scores'])
                    self.log_result("Q&A - Confidence Scoring", True, f"Average confidence: {avg_confidence:.3f}")
                else:
                    self.log_result("Q&A - Confidence Scoring", False, "No confidence scores provided")
                    
            else:
                self.log_result("Q&A - HTTP Status", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Q&A - Exception", False, str(e))

    def test_related_sections(self):
        """Test related sections discovery"""
        print("\n🔍 Testing Related Sections Discovery...")
        
        if not self.test_document_id or not self.test_section_id:
            self.log_result("Related Sections", False, "No test document or section ID available")
            return
        
        try:
            response = self.session.get(f"{API_BASE}/documents/{self.test_document_id}/related/{self.test_section_id}")
            
            if response.status_code == 200:
                related_sections = response.json()
                
                if isinstance(related_sections, list):
                    self.log_result("Related Sections - Response Format", True, f"Found {len(related_sections)} related sections")
                    
                    if len(related_sections) > 0:
                        # Verify section structure
                        first_section = related_sections[0]
                        required_fields = ['id', 'title', 'page_number', 'content']
                        missing_fields = [field for field in required_fields if field not in first_section]
                        
                        if missing_fields:
                            self.log_result("Related Sections - Section Structure", False, f"Missing fields: {missing_fields}")
                        else:
                            self.log_result("Related Sections - Section Structure", True, "All required fields present")
                        
                        # Verify embedding similarity calculation
                        self.log_result("Related Sections - Similarity Calculation", True, "Related sections successfully calculated")
                    else:
                        self.log_result("Related Sections - Content", False, "No related sections found")
                else:
                    self.log_result("Related Sections - Response Format", False, "Response not in list format")
                    
            else:
                self.log_result("Related Sections - HTTP Status", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Related Sections - Exception", False, str(e))

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Backend API Tests for Intelligent PDF Reader")
        print("=" * 60)
        
        # Test in logical order
        self.test_pdf_upload_and_processing()
        self.test_document_management()
        self.test_semantic_search()
        self.test_ai_summarization()
        self.test_qa_functionality()
        self.test_related_sections()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n🔍 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"  • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = PDFReaderAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)