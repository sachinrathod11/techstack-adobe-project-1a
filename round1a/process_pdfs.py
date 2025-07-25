#!/usr/bin/env python3
"""
Optimized PyMuPDF-based PDF outline extractor for Adobe Hackathon Round 1A
Reduced memory footprint and improved efficiency for Docker deployment
"""

import json
import statistics
import fitz  # PyMuPDF
from pathlib import Path
from itertools import groupby
from operator import itemgetter

INPUT = Path("/app/input")
OUTPUT = Path("/app/output")
OUTPUT.mkdir(parents=True, exist_ok=True)

def extract_spans(doc):
    """Extract text spans with minimal memory usage"""
    spans = []
    for pno, page in enumerate(doc):
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES)["blocks"]
        for block in blocks:
            if block["type"] != 0:  # Skip non-text blocks
                continue
            for ln_no, line in enumerate(block["lines"], 1):
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text and len(text) > 1:  # Skip empty and single-char spans
                        spans.append({
                            "page": pno,
                            "line": (pno, ln_no),
                            "x": span["origin"][0],
                            "size": round(span["size"], 1),  # Round to reduce precision
                            "bold": bool(span["flags"] & 2),
                            "text": text
                        })
    return spans

def merge_lines(spans):
    """Efficiently merge spans into complete lines"""
    if not spans:
        return []

    # Sort once
    spans.sort(key=itemgetter("line", "x"))

    lines = []
    for _, group in groupby(spans, key=itemgetter("line")):
        group_list = list(group)
        if not group_list:
            continue

        # Merge text
        text = " ".join(s["text"] for s in group_list).strip()
        if not text:
            continue

        # Use the largest font size as representative
        ref_span = max(group_list, key=lambda s: s["size"])

        lines.append({
            "page": ref_span["page"],
            "text": text,
            "size": ref_span["size"],
            "bold": ref_span["bold"]
        })

    return lines

def classify_headings(lines):
    """Classify lines into heading levels using font analysis"""
    if not lines:
        return None, []

    # Get font sizes for analysis
    sizes = [ln["size"] for ln in lines]

    # Use mode for body text detection, with fallback to median
    try:
        body_size = statistics.mode(sizes)
    except statistics.StatisticsError:
        body_size = statistics.median(sizes)

    title = None
    outline = []

    for ln in lines:
        size_ratio = ln["size"] / body_size

        # Classify based on size ratios and formatting
        if size_ratio >= 1.8:
            level = "TITLE"
        elif size_ratio >= 1.4:
            level = "H1"
        elif size_ratio >= 1.2:
            level = "H2"
        elif size_ratio >= 1.05 or ln["bold"]:
            level = "H3"
        else:
            continue

        # Handle title vs headings
        if level == "TITLE" and title is None:
            title = ln["text"]
        else:
            outline.append({
                "level": level,
                "text": ln["text"],
                "page": ln["page"] + 1
            })

    return title, outline

def process_pdf(pdf_path):
    """Process a single PDF with memory-efficient approach"""
    try:
        with fitz.open(pdf_path) as doc:
            spans = extract_spans(doc)

        # Process extracted data
        lines = merge_lines(spans)
        title, outline = classify_headings(lines)

        return {
            "title": title or pdf_path.stem,
            "outline": outline
        }

    except Exception as e:
        print(f"Error processing {pdf_path.name}: {e}")
        return {
            "title": pdf_path.stem,
            "outline": []
        }

def main():
    """Main processing loop"""
    pdf_files = list(INPUT.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in /app/input")
        return

    for pdf_path in pdf_files:
        result = process_pdf(pdf_path)

        # Write output
        output_file = OUTPUT / f"{pdf_path.stem}.json"
        try:
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"✓ {pdf_path.name} → {output_file.name}")
        except Exception as e:
            print(f"Error writing {output_file.name}: {e}")

if __name__ == "__main__":
    main()
