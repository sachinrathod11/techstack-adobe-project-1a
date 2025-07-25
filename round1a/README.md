# Adobe Hackathon Round 1A - PDF Outline Extractor

**A lightweight, offline PDF outline extraction solution using pypdf**

## Overview

This solution extracts structured document outlines (title and H1-H3 headings) from PDF files for the Adobe "Connecting the Dots" hackathon Round 1A challenge.

## Technical Approach

- **Pure Python implementation** using pypdf library
- **Font-based heading detection** via relative size analysis
- **Visual line assembly** from text fragments
- **Docker containerization** for consistent deployment

## Key Features

- ✅ **Offline operation** - No network dependencies
- ✅ **Small footprint** - ~70MB Docker image
- ✅ **Fast processing** - <10s for 50-page PDFs
- ✅ **Generic logic** - No hard-coded document patterns
- ✅ **AMD64 compatible** - Meets hackathon requirements

## Libraries Used

- **pypdf 5.7*** - Pure Python PDF parsing
- **Python 3.11** - Runtime environment
- **Docker** - Containerization platform

## Architecture

```
Input PDFs → Text Extraction → Line Assembly → Heading Classification → JSON Output
```

1. **Text Extraction**: Extract text spans with font metadata
2. **Line Assembly**: Group adjacent spans into visual lines
3. **Heading Classification**: Identify headings using relative font sizes
4. **Output Generation**: Export structured JSON format

## File Structure

```
.
├── Dockerfile              # Container definition
├── process_pdfs.py         # Main extraction logic
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Usage

**Build:**
```bash
docker build --platform linux/amd64 -t pdf-outline:latest .
```

**Run:**
```bash
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none pdf-outline:latest
```

## Output Format

```json
{
  "title": "Document Title",
  "outline": [
    {"level": "H1", "text": "Main Heading", "page": 1},
    {"level": "H2", "text": "Sub Heading", "page": 2}
  ]
}
```

## Constraints Met

| Requirement | Status |
|-------------|---------|
| Image size ≤200MB | ✅ ~70MB |
| Runtime ≤10s/50 pages | ✅ ~3-7s |
| CPU-only, AMD64 | ✅ |
| Offline operation | ✅ |
| No hard-coding | ✅ |

## Algorithm Details

**Heading Detection Logic:**
- Extract body font size using statistical mode
- Classify text lines based on relative font ratios:
  - Title: ≥1.8× body size
  - H1: ≥1.4× body size  
  - H2: ≥1.2× body size
  - H3: ≥1.05× body size or bold text

**Error Handling:**
- Statistics error fallback for font size detection
- Empty document handling
- Graceful parsing failures

## Performance

- **Memory usage**: <60MB RSS
- **Processing speed**: ~3-7s per 50-page PDF
- **Accuracy**: Robust across document types
