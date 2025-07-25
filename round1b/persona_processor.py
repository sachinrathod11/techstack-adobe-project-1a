import os
import json
from pathlib import Path
from pypdf import PdfReader
from datetime import datetime
import re
from collections import defaultdict, Counter

class PersonaBasedDocumentProcessor:
    def __init__(self):
        self.persona_keywords = []
        self.job_keywords = []
        self.domain_patterns = {
            'travel': ['destination', 'hotel', 'restaurant', 'attraction', 'transport', 'booking', 'itinerary', 'sightseeing'],
            'research': ['methodology', 'analysis', 'data', 'study', 'findings', 'experiment', 'survey', 'results'],
            'business': ['strategy', 'market', 'revenue', 'customer', 'product', 'sales', 'profit', 'ROI'],
            'education': ['learning', 'student', 'course', 'curriculum', 'degree', 'academic', 'university', 'college'],
            'healthcare': ['patient', 'treatment', 'medical', 'diagnosis', 'therapy', 'health', 'clinical', 'medicine'],
            'technology': ['software', 'development', 'programming', 'system', 'application', 'digital', 'tech', 'IT']
        }

    def load_persona_and_job(self, input_dir):
        try:
            # Load persona
            persona_file = input_dir / "persona.json"
            if persona_file.exists():
                with open(persona_file, 'r', encoding='utf-8') as f:
                    persona_data = json.load(f)
                self.extract_persona_keywords(persona_data)

            # Load job description
            job_file = input_dir / "job.json" 
            if job_file.exists():
                with open(job_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                self.extract_job_keywords(job_data)

            return persona_data, job_data

        except Exception as e:
            print(f"Error loading persona/job files: {e}")
            return {}, {}

    def extract_persona_keywords(self, persona_data):
        self.persona_keywords = []

        # Extract from various persona fields
        text_fields = ['description', 'background', 'goals', 'pain_points', 'interests', 'role', 'title']

        for field in text_fields:
            if field in persona_data and isinstance(persona_data[field], str):
                text = persona_data[field].lower()
                words = re.findall(r'\b\w{3,}\b', text)  # Extract words 3+ chars
                self.persona_keywords.extend(words)

        # Remove duplicates and common words
        common_words = {'the', 'and', 'but', 'for', 'are', 'with', 'this', 'that', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'work'}
        self.persona_keywords = list(set([k for k in self.persona_keywords if k not in common_words]))

    def extract_job_keywords(self, job_data):
        self.job_keywords = []

        # Extract from job fields
        text_fields = ['description', 'requirements', 'responsibilities', 'objectives', 'deliverables', 'title', 'goals']

        for field in text_fields:
            if field in job_data and isinstance(job_data[field], str):
                text = job_data[field].lower()
                words = re.findall(r'\b\w{3,}\b', text)
                self.job_keywords.extend(words)

        # Clean up
        common_words = {'the', 'and', 'but', 'for', 'are', 'with', 'this', 'that', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'work'}
        self.job_keywords = list(set([k for k in self.job_keywords if k not in common_words]))

    def extract_document_sections(self, pdf_path):
        try:
            reader = PdfReader(pdf_path)
            sections = []

            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                page_sections = self.detect_sections_in_text(text, page_num)
                sections.extend(page_sections)

            return sections

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return []

    def detect_sections_in_text(self, text, page_num):
        sections = []
        lines = text.split('\n')

        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line is a section heading
            if self.is_section_heading(line):
                # Save previous section
                if current_section and current_content:
                    sections.append({
                        'title': current_section,
                        'content': ' '.join(current_content),
                        'page_num': page_num
                    })

                # Start new section  
                current_section = line
                current_content = []
            else:
                # Add to current section content
                if current_section:
                    current_content.append(line)

        # Don't forget the last section
        if current_section and current_content:
            sections.append({
                'title': current_section,
                'content': ' '.join(current_content), 
                'page_num': page_num
            })

        return sections

    def is_section_heading(self, line):
        if len(line) < 3 or len(line) > 100:
            return False

        # Pattern matching for headings
        patterns = [
            r'^\d+\.?\s+.+',                    # "1. Introduction"
            r'^\d+\.\d+\.?\s+.+',             # "1.1 Overview"  
            r'^[A-Z][A-Z\s]{2,50}$',              # "INTRODUCTION"
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:?$', # "Chapter One:"
            r'^Chapter\s+\d+',                   # "Chapter 1"
            r'^Section\s+\d+',                   # "Section 1"
        ]

        return any(re.match(pattern, line) for pattern in patterns)

    def calculate_relevance_score(self, section):
        content_text = (section['title'] + ' ' + section['content']).lower()
        words = re.findall(r'\b\w{3,}\b', content_text)

        if not words:
            return 0.0

        score = 0.0

        # Persona keyword matching (2x weight)
        persona_matches = sum(1 for word in words if word in self.persona_keywords)
        score += (persona_matches / len(words)) * 20

        # Job keyword matching (3x weight)  
        job_matches = sum(1 for word in words if word in self.job_keywords)
        score += (job_matches / len(words)) * 30

        # Domain pattern matching
        for domain, keywords in self.domain_patterns.items():
            domain_matches = sum(1 for word in words if word in keywords)
            if domain_matches > 0:
                score += (domain_matches / len(words)) * 10

        # Content quality factors
        length_score = min(len(content_text) / 100, 5)  # Longer content gets bonus
        sentence_count = content_text.count('.') + content_text.count('!') + content_text.count('?')
        sentence_score = min(sentence_count / 3, 3)  # Well-structured content

        # Structural elements (tables, lists, etc.)
        structure_score = 0
        if '•' in content_text or '\n-' in content_text:
            structure_score += 2
        if any(word in content_text for word in ['table', 'figure', 'chart', 'graph']):
            structure_score += 1
        if re.search(r'\d+%|\$\d+|\d+\.\d+', content_text):  # Numbers/stats
            structure_score += 1

        total_score = score + length_score + sentence_score + structure_score
        return round(min(total_score, 10.0), 1)  # Cap at 10.0

    def refine_section_content(self, section, max_chars=500):
        content = section['content']

        if len(content) <= max_chars:
            return content

        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        scored_sentences = []

        for sentence in sentences:
            if len(sentence.strip()) < 10:
                continue

            # Score each sentence for relevance
            words = re.findall(r'\b\w{3,}\b', sentence.lower())
            sentence_score = 0

            # Persona/job keyword bonus
            persona_matches = sum(1 for word in words if word in self.persona_keywords)
            job_matches = sum(1 for word in words if word in self.job_keywords)
            sentence_score = persona_matches * 2 + job_matches * 3

            scored_sentences.append((sentence_score, sentence.strip()))

        # Select top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        selected_sentences = [s[1] for s in scored_sentences[:3]]  # Top 3 sentences

        refined_content = '. '.join(selected_sentences)
        if len(refined_content) > max_chars:
            refined_content = refined_content[:max_chars-3] + '...'

        return refined_content

def process_persona_documents():
    input_dir = Path("/app/input")
    output_dir = Path("/app/output") 

    output_dir.mkdir(parents=True, exist_ok=True)

    processor = PersonaBasedDocumentProcessor()

    # Load persona and job data
    persona_data, job_data = processor.load_persona_and_job(input_dir)

    if not persona_data and not job_data:
        print("Warning: No persona.json or job.json found. Using default processing.")

    # Find PDF files
    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in input directory")
        return

    # Process all documents
    all_sections = []
    input_documents = []

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        input_documents.append(pdf_file.name)

        sections = processor.extract_document_sections(pdf_file)

        for section in sections:
            section['document'] = pdf_file.name
            section['relevance_score'] = processor.calculate_relevance_score(section)
            all_sections.append(section)

    # Sort sections by relevance score
    all_sections.sort(key=lambda x: x['relevance_score'], reverse=True)

    # Select top sections for extraction
    top_sections = all_sections[:5]  # Top 5 most relevant

    # Create extracted sections
    extracted_sections = []
    for i, section in enumerate(top_sections, 1):
        extracted_sections.append({
            "document": section['document'],
            "section_title": section['title'],
            "importance_rank": i,
            "page_number": section['page_num']
        })

    # Create subsection analysis
    subsection_analysis = []
    for section in top_sections:
        refined_content = processor.refine_section_content(section)

        subsection_analysis.append({
            "document": section['document'],
            "refined_text": refined_content,
            "page_number": section['page_num']
        })

    # Create final output
    result = {
        "metadata": {
            "input_documents": input_documents,
            "persona": persona_data.get("title", "Unknown") if persona_data else "Default",
            "job_to_be_done": job_data.get("description", "General analysis") if job_data else "Document analysis",
            "processing_timestamp": datetime.now().isoformat()
        },
        "extracted_sections": extracted_sections,
        "subsection_analysis": subsection_analysis
    }

    # Save result
    output_file = output_dir / "challenge1b_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✓ Processing complete!")
    print(f"✓ Total sections analyzed: {len(all_sections)}")
    print(f"✓ Top sections selected: {len(extracted_sections)}")
    print(f"✓ Output saved to: {output_file}")

if __name__ == "__main__":
    print("Adobe Hackathon Round 1B - Persona-Based Document Processor")
    print("="*60)
    process_persona_documents()
    print("="*60)
    print("Processing complete!")
