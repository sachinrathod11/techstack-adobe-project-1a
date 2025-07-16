#!/usr/bin/env python3
"""
Round 1A: PDF Outline Extractor for Hackathon
Extracts title and headings (H1, H2, H3) from PDF files
Outputs structured JSON format as required
"""

import PyPDF2
import json
import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from collections import Counter

# Download required NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

class PDFOutlineExtractor:
    def __init__(self):
        self.title_patterns = [
            r'^[A-Z][A-Z\s]{5,}$',  # ALL CAPS titles
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Title Case
            r'^\d+\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Numbered titles
        ]
        
        self.heading_patterns = [
            # H1 patterns
            (r'^[A-Z][A-Z\s]{3,}$', 1),  # ALL CAPS
            (r'^\d+\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', 1),  # 1. Chapter
            (r'^CHAPTER\s+\d+', 1),  # CHAPTER X
            (r'^SECTION\s+\d+', 1),  # SECTION X
            (r'^PART\s+\d+', 1),  # PART X
            
            # H2 patterns
            (r'^\d+\.\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', 2),  # 1.1 Section
            (r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:$', 2),  # Title Case with colon
            (r'^\d+\.\d+\s+[A-Z]', 2),  # 1.1 General pattern
            
            # H3 patterns
            (r'^\d+\.\d+\.\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', 3),  # 1.1.1 Subsection
            (r'^[a-z]\)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', 3),  # a) Item
            (r'^\([a-z]\)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', 3),  # (a) Item
            (r'^\d+\.\d+\.\d+\s+[A-Z]', 3),  # 1.1.1 General pattern
        ]

    def extract_text_from_pdf(self, pdf_path: str) -> tuple[str, int]:
        """Extract text from PDF file and return content with page count"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                page_count = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    text += f"\n--- Page {page_num} ---\n{page_text}\n"
                
                return text, page_count
        except Exception as e:
            print(f"Error extracting PDF {pdf_path}: {str(e)}")
            return "", 0

    def detect_title(self, text: str) -> str:
        """Detect document title from the first page"""
        lines = text.split('\n')
        first_page_lines = []
        
        # Get first page content
        for line in lines:
            if line.startswith("--- Page 2 ---"):
                break
            if not line.startswith("--- Page 1 ---") and line.strip():
                first_page_lines.append(line.strip())
        
        # Try to find title in first few lines
        for line in first_page_lines[:10]:  # Check first 10 lines
            if len(line) > 5 and len(line) < 100:  # Reasonable title length
                # Check title patterns
                for pattern in self.title_patterns:
                    if re.match(pattern, line):
                        return line
                
                # Check if line looks like a title (proper case, not too common words)
                words = line.split()
                if len(words) >= 2 and len(words) <= 10:
                    # Check if it's not a common sentence pattern
                    if not any(word.lower() in ['the', 'this', 'that', 'these', 'those', 'a', 'an'] for word in words[:2]):
                        if line[0].isupper() and not line.endswith('.'):
                            return line
        
        # Fallback: use first substantial line
        for line in first_page_lines:
            if len(line) > 10 and len(line) < 100:
                return line
        
        return "Untitled Document"

    def detect_headings(self, text: str) -> List[Dict[str, Any]]:
        """Detect headings with their levels and page numbers"""
        lines = text.split('\n')
        headings = []
        current_page = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for page markers
            if line.startswith("--- Page ") and line.endswith(" ---"):
                try:
                    current_page = int(line.split()[2])
                except:
                    pass
                continue
            
            # Check heading patterns
            for pattern, level in self.heading_patterns:
                if re.match(pattern, line):
                    # Additional validation
                    if self.is_valid_heading(line, level):
                        headings.append({
                            "level": f"H{level}",
                            "text": line,
                            "page": current_page
                        })
                    break
        
        return headings

    def is_valid_heading(self, text: str, level: int) -> bool:
        """Validate if text is actually a heading"""
        # Skip if too long (likely not a heading)
        if len(text) > 150:
            return False
        
        # Skip if contains common non-heading patterns
        non_heading_patterns = [
            r'^\d+\s*$',  # Just numbers
            r'^page\s+\d+',  # Page numbers
            r'^\d+\.\s*$',  # Just numbered points
            r'^figure\s+\d+',  # Figure captions
            r'^table\s+\d+',  # Table captions
            r'^appendix\s+[a-z]$',  # Simple appendix
        ]
        
        text_lower = text.lower()
        for pattern in non_heading_patterns:
            if re.match(pattern, text_lower):
                return False
        
        # Additional validation for different levels
        if level == 1:
            # H1 should be substantial
            return len(text.split()) >= 1 and len(text.split()) <= 15
        elif level == 2:
            # H2 should be reasonable length
            return len(text.split()) >= 1 and len(text.split()) <= 20
        elif level == 3:
            # H3 can be shorter
            return len(text.split()) >= 1 and len(text.split()) <= 25
        
        return True

    def post_process_headings(self, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process headings to remove duplicates and improve quality"""
        seen_texts = set()
        processed_headings = []
        
        for heading in headings:
            text = heading["text"]
            
            # Remove duplicates
            if text in seen_texts:
                continue
            seen_texts.add(text)
            
            # Clean up text
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = text.strip()
            
            if text:
                heading["text"] = text
                processed_headings.append(heading)
        
        return processed_headings

    def extract_outline(self, pdf_path: str) -> Dict[str, Any]:
        """Extract complete outline from PDF"""
        # Extract text
        text, page_count = self.extract_text_from_pdf(pdf_path)
        if not text:
            return {"title": "Error Processing PDF", "outline": []}
        
        # Detect title
        title = self.detect_title(text)
        
        # Detect headings
        headings = self.detect_headings(text)
        
        # Post-process headings
        headings = self.post_process_headings(headings)
        
        # Sort by page number and then by appearance
        headings.sort(key=lambda x: x["page"])
        
        return {
            "title": title,
            "outline": headings
        }

def process_pdf_directory(input_dir: str, output_dir: str):
    """Process all PDF files in input directory"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize extractor
    extractor = PDFOutlineExtractor()
    
    # Process all PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in input directory")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    for pdf_file in pdf_files:
        try:
            print(f"Processing: {pdf_file.name}")
            
            # Extract outline
            outline = extractor.extract_outline(str(pdf_file))
            
            # Create output JSON file
            output_file = output_path / f"{pdf_file.stem}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(outline, f, indent=2, ensure_ascii=False)
            
            print(f"Generated: {output_file.name}")
            print(f"  Title: {outline['title']}")
            print(f"  Headings: {len(outline['outline'])}")
            
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {str(e)}")
            
            # Create error output
            error_output = {
                "title": f"Error Processing {pdf_file.name}",
                "outline": []
            }
            
            output_file = output_path / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(error_output, f, indent=2, ensure_ascii=False)

def main():
    """Main entry point for the hackathon solution"""
    input_dir = "/app/input"
    output_dir = "/app/output"
    
    # Check if directories exist
    if not os.path.exists(input_dir):
        print(f"Input directory {input_dir} does not exist")
        sys.exit(1)
    
    print("PDF Outline Extractor - Round 1A")
    print("=" * 40)
    
    # Process PDFs
    process_pdf_directory(input_dir, output_dir)
    
    print("=" * 40)
    print("Processing complete!")

if __name__ == "__main__":
    main()