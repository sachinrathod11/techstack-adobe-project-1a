#!/usr/bin/env python3
"""
Quick test for Q&A functionality fix
"""

import requests
import json
from pathlib import Path
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

def create_simple_pdf():
    """Create a simple test PDF"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Test Document")
    p.drawString(100, 720, "This is a simple test document for Q&A testing.")
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

def test_qa_fix():
    session = requests.Session()
    
    # Upload a document first
    pdf_content = create_simple_pdf()
    files = {'file': ('test.pdf', pdf_content, 'application/pdf')}
    response = session.post(f"{API_BASE}/documents/upload", files=files)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        return False
    
    doc_id = response.json()['id']
    print(f"✅ Document uploaded: {doc_id}")
    
    # Test Q&A endpoint (should fail gracefully due to OpenAI quota, but not crash)
    qa_data = {
        "document_id": doc_id,
        "question": "What is this document about?",
        "context_limit": 2
    }
    
    response = session.post(f"{API_BASE}/documents/{doc_id}/qa", json=qa_data)
    
    if response.status_code == 500:
        error_detail = response.json().get('detail', '')
        if 'KeyError' in error_detail:
            print(f"❌ Q&A still has KeyError bug: {error_detail}")
            return False
        elif 'quota' in error_detail or 'OpenAI' in error_detail:
            print(f"✅ Q&A bug fixed - now failing gracefully due to OpenAI quota: {response.status_code}")
            return True
        else:
            print(f"❌ Q&A has different error: {error_detail}")
            return False
    elif response.status_code == 200:
        print(f"✅ Q&A working perfectly: {response.status_code}")
        return True
    else:
        print(f"❌ Q&A unexpected status: {response.status_code}")
        return False

if __name__ == "__main__":
    success = test_qa_fix()
    print(f"Q&A Fix Test: {'PASSED' if success else 'FAILED'}")