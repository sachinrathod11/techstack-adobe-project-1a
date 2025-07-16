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
import openai
import json
import tiktoken
import re
import numpy as np
from sentence_transformers import SentenceTransformer
import base64


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI client
openai.api_key = os.environ['OPENAI_API_KEY']
openai_client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# Initialize sentence transformer for embeddings
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

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
    max_length: int = 500

class QARequest(BaseModel):
    document_id: str
    question: str
    context_limit: int = 3

def extract_text_from_pdf(file_content: bytes) -> tuple[str, int]:
    """Extract text from PDF file and return content with page count"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        page_count = len(pdf_reader.pages)
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            text += f"\n--- Page {page_num} ---\n{page_text}\n"
        
        return text, page_count
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

# API Routes
@api_router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a PDF document"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Read file content
    file_content = await file.read()
    
    # Extract text and page count
    text, page_count = extract_text_from_pdf(file_content)
    
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
        'embedding_segments': embedding_segments
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
    """Summarize a document or specific section"""
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
        content = document['content'][:4000]  # Limit content for API
        title = document['title']
    
    # Generate summary using OpenAI
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a helpful assistant that creates concise summaries. Summarize the following text in {request.max_length} words or less."
                },
                {
                    "role": "user",
                    "content": f"Title: {title}\n\nContent: {content}"
                }
            ],
            max_tokens=min(request.max_length * 2, 1000),
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        
        return {
            "summary": summary,
            "title": title,
            "word_count": len(summary.split())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@api_router.post("/documents/{document_id}/qa")
async def answer_question(document_id: str, request: QARequest):
    """Answer questions about the document"""
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
    
    # Create context string
    context_text = "\n\n".join([f"Section: {ctx['title']}\nContent: {ctx['content']}" for ctx, _ in top_contexts])
    
    # Generate answer using OpenAI
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions based on the provided document context. Only answer based on the given context, and mention if the answer is not found in the context."
                },
                {
                    "role": "user",
                    "content": f"Context from document:\n{context_text}\n\nQuestion: {request.question}"
                }
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        return {
            "answer": answer,
            "question": request.question,
            "relevant_sections": [ctx[0]['id'] for ctx, _ in top_contexts],
            "confidence_scores": [sim for _, sim in top_contexts]
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