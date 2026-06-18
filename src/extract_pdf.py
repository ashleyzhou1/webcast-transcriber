"""
extract_pdf.py

Given a local PDF file, extracts its plain text content. No AI/ML
involved here -- PDFs that contain real text (not scanned images) already
have that text embedded in the file; this just pulls it out directly.

Note: this will NOT work well on scanned/image-only PDFs (e.g. a PDF that's
just a photo of a printed page). Those would need OCR instead, which is a
different, heavier tool -- worth flagging as a known limitation rather than
something this script handles.

Usage (standalone):
    python extract_pdf.py path/to/document.pdf

Usage (as a module):
    from extract_pdf import extract_text_from_pdf
    result = extract_text_from_pdf("path/to/document.pdf")
"""

import sys
import json
from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str) -> dict:
    """
    Extract text from a local PDF file.

    Returns a dict with keys: text (full extracted text, pages joined
    with blank lines), num_pages, source_file.
    """
    pdf_path = str(pdf_path)
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(pdf_path)
    page_texts = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_texts.append(page_text.strip())

    full_text = "\n\n".join(page_texts)

    if not full_text.strip():
        print(
            "Warning: no text was extracted. This PDF may be scanned/"
            "image-only, which requires OCR rather than direct extraction."
        )

    return {
        "text": full_text,
        "num_pages": len(reader.pages),
        "source_file": pdf_path,
    }


def save_extracted_text(result: dict, output_path: str):
    """Save extracted text to a .txt file and metadata to a .json file,
    matching the same pattern used by transcribe.py for consistency."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    txt_path = output_path.with_suffix(".txt")
    txt_path.write_text(result["text"], encoding="utf-8")

    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Saved extracted text to: {txt_path}")
    print(f"Saved metadata to: {json_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf.py <pdf_path> [output_dir]")
        sys.exit(1)

    pdf_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "../samples"

    result = extract_text_from_pdf(pdf_file)

    print(f"\n--- EXTRACTED TEXT PREVIEW (first 500 chars) ---")
    print(result["text"][:500])
    print(f"\n[Extracted {result['num_pages']} page(s) from {pdf_file}]")

    out_name = Path(pdf_file).stem
    save_extracted_text(result, f"{output_dir}/{out_name}")