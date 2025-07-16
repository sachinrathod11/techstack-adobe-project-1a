from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import PyPDF2
import io
import json
import tiktoken
import re
import numpy as np
from sentence_transformers import SentenceTransformer
import base64
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from collections import Counter
import heapq


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize sentence transformer for embeddings (cached locally)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize text processing tools
stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class DocumentCreate(BaseModel):
    title: str
    content: str
    total_pages: int

class DocumentResponse(BaseModel):
    id: str
    title: str
    content: str
    total_pages: int
    created_at: datetime
    structure: List[Dict[str, Any]]
    embedding_segments: List[Dict[str, Any]]
    pdf_base64: Optional[str] = None

class DocumentSection(BaseModel):
    id: str
    document_id: str
    title: str
    content: str
    page_number: int
    level: int  # H1=1, H2=2, etc.
    start_char: int
    end_char: int
    embedding: List[float]

class SearchQuery(BaseModel):
    document_id: str
    query: str
    limit: int = 10

class SearchResult(BaseModel):
    section_id: str
    title: str
    content: str
    page_number: int
    similarity_score: float
    related_sections: List[str]

class SummarizeRequest(BaseModel):
    document_id: str
    section_id: Optional[str] = None
    max_length: int = 5

class QARequest(BaseModel):
    document_id: str
    question: str
    context_limit: int = 3

def extract_text_from_pdf(file_content: bytes) -> tuple[str, int, str]:
    """Extract text from PDF file and return content, page count, and base64 PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        page_count = len(pdf_reader.pages)
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            text += f"\n--- Page {page_num} ---\n{page_text}\n"
        
        # Convert PDF to base64 for frontend
        pdf_base64 = base64.b64encode(file_content).decode('utf-8')
        
        return text, page_count, pdf_base64
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting PDF: {str(e)}")

def detect_document_structure(text: str) -> List[Dict[str, Any]]:
    """Detect headings and structure in the document"""
    lines = text.split('\n')
    structure = []
    current_page = 1
    char_position = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            char_position += 1
            continue
            
        # Check for page markers
        if line.startswith("--- Page ") and line.endswith(" ---"):
            current_page = int(line.split()[2])
            char_position += len(line) + 1
            continue
        
        # Detect headings based on patterns
        level = 0
        title = line
        
        # Check for common heading patterns
        if re.match(r'^[A-Z][A-Z\s]{3,}$', line):  # ALL CAPS
            level = 1
        elif re.match(r'^\d+\.\s+[A-Z]', line):  # 1. Chapter
            level = 1
        elif re.match(r'^\d+\.\d+\s+[A-Z]', line):  # 1.1 Section
            level = 2
        elif re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*:?$', line):  # Title Case
            level = 2
        elif len(line) < 100 and not line.endswith('.') and any(c.isupper() for c in line):
            level = 3
        
        if level > 0:
            structure.append({
                'id': str(uuid.uuid4()),
                'title': title,
                'level': level,
                'page_number': current_page,
                'start_char': char_position,
                'end_char': char_position + len(line),
                'content': line
            })
        
        char_position += len(line) + 1
    
    return structure

def create_embedding_segments(text: str, structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create text segments with embeddings for semantic search"""
    segments = []
    
    # If we have structure, create segments based on sections
    if structure:
        text_chars = list(text)
        for i, section in enumerate(structure):
            # Get content between this section and next section
            start_pos = section['start_char']
            end_pos = structure[i + 1]['start_char'] if i + 1 < len(structure) else len(text)
            
            segment_text = ''.join(text_chars[start_pos:end_pos]).strip()
            
            if len(segment_text) > 50:  # Only create segments for substantial content
                embedding = embedding_model.encode(segment_text).tolist()
                segments.append({
                    'id': str(uuid.uuid4()),
                    'section_id': section['id'],
                    'title': section['title'],
                    'content': segment_text[:1000],  # Limit content size
                    'page_number': section['page_number'],
                    'embedding': embedding
                })
    else:
        # Create segments by splitting text into chunks
        chunks = [text[i:i+1000] for i in range(0, len(text), 800)]  # 200 char overlap
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) > 50:
                embedding = embedding_model.encode(chunk).tolist()
                segments.append({
                    'id': str(uuid.uuid4()),
                    'section_id': f"chunk_{i}",
                    'title': f"Chunk {i+1}",
                    'content': chunk,
                    'page_number': 1,  # Default page
                    'embedding': embedding
                })
    
    return segments

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    a = np.array(embedding1)
    b = np.array(embedding2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def find_related_sections(target_segment: Dict[str, Any], all_segments: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    """Find related sections based on embedding similarity"""
    similarities = []
    target_embedding = target_segment['embedding']
    
    for segment in all_segments:
        if segment['id'] != target_segment['id']:
            similarity = calculate_similarity(target_embedding, segment['embedding'])
            similarities.append((segment['id'], similarity))
    
    # Sort by similarity and return top matches
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [seg_id for seg_id, _ in similarities[:limit]]

def preprocess_text(text: str) -> List[str]:
    """Preprocess text for summarization"""
    # Remove page markers and clean text
    text = re.sub(r'--- Page \d+ ---', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Tokenize into sentences
    sentences = sent_tokenize(text)
    
    # Clean sentences
    cleaned_sentences = []
    for sentence in sentences:
        # Remove very short sentences
        if len(sentence.split()) > 5:
            cleaned_sentences.append(sentence.strip())
    
    return cleaned_sentences

def calculate_sentence_scores(sentences: List[str], title: str = "") -> Dict[str, float]:
    """Calculate importance scores for sentences using TF-IDF"""
    # Combine title with sentences for better context
    all_text = [title] + sentences if title else sentences
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
    
    try:
        tfidf_matrix = vectorizer.fit_transform(all_text)
        
        # Calculate average TF-IDF score for each sentence
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            if i + (1 if title else 0) < tfidf_matrix.shape[0]:
                score = tfidf_matrix[i + (1 if title else 0)].mean()
                sentence_scores[sentence] = score
            else:
                sentence_scores[sentence] = 0.0
                
        return sentence_scores
    except:
        # Fallback to length-based scoring
        return {sentence: len(sentence.split()) for sentence in sentences}

def extract_summary_offline(text: str, title: str = "", max_sentences: int = 5) -> str:
    """Generate extractive summary using TF-IDF"""
    sentences = preprocess_text(text)
    
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    
    # Calculate sentence scores
    sentence_scores = calculate_sentence_scores(sentences, title)
    
    # Get top sentences
    top_sentences = heapq.nlargest(max_sentences, sentence_scores.items(), key=lambda x: x[1])
    
    # Sort by original order
    summary_sentences = []
    for sentence, score in top_sentences:
        summary_sentences.append(sentence)
    
    # Sort by position in original text
    summary_sentences.sort(key=lambda x: sentences.index(x) if x in sentences else 0)
    
    return " ".join(summary_sentences)

def answer_question_offline(question: str, context_segments: List[Dict[str, Any]]) -> str:
    """Answer question using keyword matching and context similarity"""
    # Extract keywords from question
    question_words = set(word_tokenize(question.lower()))
    question_words = {word for word in question_words if word not in stop_words and word.isalpha()}
    
    if not question_words:
        return "I couldn't understand the question. Please try rephrasing it."
    
    # Find best matching segments
    best_matches = []
    for segment in context_segments:
        content = segment['content'].lower()
        content_words = set(word_tokenize(content))
        
        # Calculate keyword overlap
        overlap = len(question_words.intersection(content_words))
        if overlap > 0:
            score = overlap / len(question_words)
            best_matches.append((segment, score))
    
    if not best_matches:
        return "I couldn't find relevant information to answer your question."
    
    # Sort by relevance
    best_matches.sort(key=lambda x: x[1], reverse=True)
    
    # Get the best matching segment
    best_segment = best_matches[0][0]
    
    # Extract relevant sentences from the best segment
    sentences = sent_tokenize(best_segment['content'])
    relevant_sentences = []
    
    for sentence in sentences:
        sentence_words = set(word_tokenize(sentence.lower()))
        if len(question_words.intersection(sentence_words)) > 0:
            relevant_sentences.append(sentence)
    
    if relevant_sentences:
        # Return the most relevant sentences
        return " ".join(relevant_sentences[:3])
    else:
        # Fallback to first part of the segment
        return best_segment['content'][:500] + "..."

# API Routes
@api_router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF document"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Read file content
    file_content = await file.read()
    
    # Extract text, page count, and base64 PDF
    text, page_count, pdf_base64 = extract_text_from_pdf(file_content)
    
    # Detect document structure
    structure = detect_document_structure(text)
    
    # Create embedding segments
    embedding_segments = create_embedding_segments(text, structure)
    
    # Save document to database
    document_data = {
        'id': str(uuid.uuid4()),
        'title': file.filename,
        'content': text,
        'total_pages': page_count,
        'created_at': datetime.utcnow(),
        'structure': structure,
        'embedding_segments': embedding_segments,
        'pdf_base64': pdf_base64
    }
    
    await db.documents.insert_one(document_data)
    
    return DocumentResponse(**document_data)

@api_router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Get a specific document by ID"""
    document = await db.documents.find_one({'id': document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(**document)

@api_router.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    """List all documents"""
    documents = await db.documents.find().to_list(100)
    return [DocumentResponse(**doc) for doc in documents]

@api_router.post("/documents/{document_id}/search", response_model=List[SearchResult])
async def search_document(document_id: str, search_query: SearchQuery):
    """Perform semantic search within a document"""
    document = await db.documents.find_one({'id': document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Generate embedding for search query
    query_embedding = embedding_model.encode(search_query.query).tolist()
    
    # Calculate similarities with all segments
    results = []
    for segment in document['embedding_segments']:
        similarity = calculate_similarity(query_embedding, segment['embedding'])
        
        # Find related sections
        related_sections = find_related_sections(segment, document['embedding_segments'])
        
        results.append(SearchResult(
            section_id=segment['id'],
            title=segment['title'],
            content=segment['content'],
            page_number=segment['page_number'],
            similarity_score=similarity,
            related_sections=related_sections
        ))
    
    # Sort by similarity and return top results
    results.sort(key=lambda x: x.similarity_score, reverse=True)
    return results[:search_query.limit]

@api_router.post("/documents/{document_id}/summarize")
async def summarize_document(document_id: str, request: SummarizeRequest):
    """Summarize a document or specific section using offline methods"""
    document = await db.documents.find_one({'id': document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get content to summarize
    if request.section_id:
        # Find specific section
        section = next((s for s in document['embedding_segments'] if s['id'] == request.section_id), None)
        if not section:
            raise HTTPException(status_code=404, detail="Section not found")
        content = section['content']
        title = section['title']
    else:
        # Summarize entire document
        content = document['content']
        title = document['title']
    
    # Generate summary using offline method
    try:
        summary = extract_summary_offline(content, title, request.max_length)
        
        return {
            "summary": summary,
            "title": title,
            "word_count": len(summary.split()),
            "method": "offline_extractive"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@api_router.post("/documents/{document_id}/qa")
async def answer_question(document_id: str, request: QARequest):
    """Answer questions about the document using offline methods"""
    document = await db.documents.find_one({'id': document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find most relevant sections for the question
    query_embedding = embedding_model.encode(request.question).tolist()
    
    # Calculate similarities and get top contexts
    contexts = []
    for segment in document['embedding_segments']:
        similarity = calculate_similarity(query_embedding, segment['embedding'])
        contexts.append((segment, similarity))
    
    # Sort by similarity and get top contexts
    contexts.sort(key=lambda x: x[1], reverse=True)
    top_contexts = contexts[:request.context_limit]
    
    # Generate answer using offline method
    try:
        context_segments = [ctx[0] for ctx in top_contexts]
        answer = answer_question_offline(request.question, context_segments)
        
        return {
            "answer": answer,
            "question": request.question,
            "relevant_sections": [ctx[0]['id'] for ctx in top_contexts],
            "confidence_scores": [sim for _, sim in top_contexts],
            "method": "offline_keyword_matching"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

@api_router.get("/documents/{document_id}/related/{section_id}")
async def get_related_sections(document_id: str, section_id: str):
    """Get related sections for a specific section"""
    document = await db.documents.find_one({'id': document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find the target section
    target_section = next((s for s in document['embedding_segments'] if s['id'] == section_id), None)
    if not target_section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Find related sections
    related_ids = find_related_sections(target_section, document['embedding_segments'], limit=5)
    
    related_sections = []
    for seg_id in related_ids:
        section = next((s for s in document['embedding_segments'] if s['id'] == seg_id), None)
        if section:
            related_sections.append({
                'id': section['id'],
                'title': section['title'],
                'page_number': section['page_number'],
                'content': section['content'][:200] + "..." if len(section['content']) > 200 else section['content']
            })
    
    return related_sections

@api_router.get("/documents/{document_id}/pdf")
async def get_pdf_content(document_id: str):
    """Get PDF content as base64 for offline viewing"""
    document = await db.documents.find_one({'id': document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if 'pdf_base64' not in document:
        raise HTTPException(status_code=404, detail="PDF content not available")
    
    return {
        "pdf_base64": document['pdf_base64'],
        "title": document['title']
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()