# PDF Outline Extractor - Round 1A Solution

## Overview
This solution extracts structured outlines from PDF documents, identifying titles and headings (H1, H2, H3) with their respective page numbers. The output is formatted as JSON according to the hackathon requirements.

## Approach

### 1. Text Extraction
- Uses PyPDF2 for robust PDF text extraction
- Maintains page number tracking throughout the document
- Handles various PDF formats and encodings

### 2. Title Detection
- Analyzes the first page content for title patterns
- Uses regex patterns to identify title-like text:
  - ALL CAPS titles
  - Title Case formatting
  - Numbered titles (e.g., "1. Introduction")
- Validates title length and structure
- Fallback to first substantial line if no pattern match

### 3. Heading Detection
- Multi-level pattern matching for H1, H2, and H3:
  - **H1**: ALL CAPS, "CHAPTER X", "SECTION X", numbered chapters
  - **H2**: Numbered sections (1.1), Title Case with colons
  - **H3**: Subsections (1.1.1), lettered items (a), (a))
- Validates heading structure and length
- Filters out false positives (figure captions, page numbers, etc.)

### 4. Post-Processing
- Removes duplicate headings
- Normalizes whitespace
- Sorts by page number and appearance order
- Quality validation for each heading level

## Libraries Used
- **PyPDF2**: PDF text extraction and parsing
- **NLTK**: Natural language processing for text tokenization
- **re**: Regular expressions for pattern matching
- **json**: JSON output formatting

## Features
- ✅ **Offline Processing**: No internet calls required
- ✅ **CPU Only**: No GPU dependencies
- ✅ **Small Size**: Under 200MB constraint
- ✅ **Fast Processing**: Optimized for <10 seconds per 50-page PDF
- ✅ **Batch Processing**: Handles multiple PDFs automatically
- ✅ **Error Handling**: Graceful handling of malformed PDFs
- ✅ **Multilingual Support**: Unicode text processing

## Docker Usage

### Build the Docker image:
```bash
docker build --platform linux/amd64 -t pdf-outline-extractor:hackathon .
```

### Run the solution:
```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-outline-extractor:hackathon
```

## Expected Input/Output
- **Input**: PDF files in `/app/input/` directory
- **Output**: JSON files in `/app/output/` directory (one per input PDF)

### Output Format:
```json
{
  "title": "Understanding AI",
  "outline": [
    { "level": "H1", "text": "Introduction", "page": 1 },
    { "level": "H2", "text": "What is AI?", "page": 2 },
    { "level": "H3", "text": "History of AI", "page": 3 }
  ]
}
```

## Algorithm Details

### Title Detection Strategy
1. Extract first page content
2. Apply title-specific regex patterns
3. Validate title characteristics (length, capitalization, structure)
4. Fallback to heuristic-based selection

### Heading Detection Strategy
1. Line-by-line text analysis
2. Pattern matching for each heading level
3. Context-aware validation
4. False positive filtering
5. Hierarchical structure preservation

### Performance Optimizations
- Efficient regex compilation
- Minimal memory footprint
- Streamlined text processing pipeline
- Early termination for obvious non-headings

## Testing Recommendations
- Test with various PDF formats (academic papers, reports, books)
- Validate with multilingual documents
- Check performance with large documents (50+ pages)
- Verify accuracy with complex hierarchical structures

## Constraints Met
- ✅ Execution time: <10 seconds for 50-page PDF
- ✅ Model size: <200MB
- ✅ Network: No internet access required
- ✅ Runtime: CPU-only, AMD64 architecture
- ✅ Memory: Optimized for 16GB RAM systems