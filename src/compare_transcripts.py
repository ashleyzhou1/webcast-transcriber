"""
compare_transcripts.py

Compares our Whisper-generated transcript against an official PDF transcript
for the same earnings call, computing Word Error Rate (WER) using jiwer.

Normalization applied before comparison:
- Strip timestamps (e.g. [05:28], [00:01:30], (05:28))
- Lowercase everything
- Strip punctuation (commas, periods, colons, etc. -- these aren't spoken)
- Normalize numbers (convert digits to words so "5" and "five" match)
- Contractions are NOT expanded ("don't" != "do not" -- treated as different)

For showing differences, uses difflib sequence alignment rather than
naive positional comparison -- so differences shown are genuine content
mismatches, not just alignment offsets from boilerplate/disclaimer text
in the official PDF that doesn't appear in the audio.

Usage:
    python compare_transcripts.py <whisper_txt> <official_pdf>

    Example:
    python compare_transcripts.py samples/6-19/whisper-output/google-q1-2026.txt samples/6-19/google-q1-2026.pdf

Requires:
    pip install jiwer num2words pypdf
"""

import sys
import re
import string
import difflib
import textwrap
from pathlib import Path

from jiwer import wer
from num2words import num2words
from pypdf import PdfReader

WRAP_WIDTH = 80


def wrap(text: str, indent: str = "  ") -> str:
    """Wrap text at WRAP_WIDTH characters with a given indent."""
    return textwrap.fill(text, width=WRAP_WIDTH, initial_indent=indent,
                         subsequent_indent=indent)


def extract_pdf_text(pdf_path: str) -> str:
    """Extract plain text from a PDF file."""
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def normalize_numbers(text: str) -> str:
    """Convert digit sequences to words so '5' and 'five' match."""
    def replace_number(match):
        num_str = match.group(0).replace(",", "")
        try:
            if "." in num_str:
                return num2words(float(num_str))
            else:
                return num2words(int(num_str))
        except Exception:
            return num_str
    return re.sub(r"\b[\d,]+\.?\d*\b", replace_number, text)


def normalize_text(text: str) -> str:
    """
    Normalize text for WER comparison:
    - Strip timestamps (e.g. [05:28], [00:01:30], (05:28))
    - Lowercase
    - Normalize numbers (digits -> words)
    - Strip punctuation
    - Collapse whitespace
    Contractions are intentionally NOT expanded.
    """
    text = re.sub(r"[\[\(]\d{1,2}:\d{2}(:\d{2})?[\]\)]", "", text)
    text = text.lower()
    text = normalize_numbers(text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_aligned_differences(reference: str, hypothesis: str) -> list[dict]:
    """
    Use difflib sequence alignment to find genuine content differences
    between the two transcripts, rather than naive positional comparison.
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    matcher = difflib.SequenceMatcher(None, ref_words, hyp_words, autojunk=False)
    differences = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        ref_chunk = " ".join(ref_words[i1:i2])
        hyp_chunk = " ".join(hyp_words[j1:j2])

        differences.append({
            "official": ref_chunk,
            "whisper": hyp_chunk,
        })

    return differences


def compare(whisper_txt_path: str, official_pdf_path: str):
    whisper_path = Path(whisper_txt_path)
    pdf_path = Path(official_pdf_path)

    if not whisper_path.exists():
        raise FileNotFoundError(f"Whisper transcript not found: {whisper_path}")
    if not pdf_path.exists():
        raise FileNotFoundError(f"Official PDF not found: {pdf_path}")

    print(f"Loading Whisper transcript: {whisper_path}")
    whisper_raw = whisper_path.read_text(encoding="utf-8")

    print(f"Extracting text from official PDF: {pdf_path}")
    official_raw = extract_pdf_text(str(pdf_path))

    print("Normalizing both transcripts...")
    whisper_norm = normalize_text(whisper_raw)
    official_norm = normalize_text(official_raw)

    print("Computing WER...\n")
    error_rate = wer(official_norm, whisper_norm)

    ref_word_count = len(official_norm.split())
    hyp_word_count = len(whisper_norm.split())

    print("=" * 60)
    print("TRANSCRIPT COMPARISON REPORT")
    print(f"Whisper transcript: {whisper_path.name}")
    print(f"Official transcript: {pdf_path.name}")
    print("=" * 60)
    print(f"Official transcript word count:  {ref_word_count:,}")
    print(f"Whisper transcript word count:   {hyp_word_count:,}")
    print(f"\nWord Error Rate (WER):  {error_rate * 100:.1f}%")

    if error_rate < 0.05:
        quality = "Excellent (< 5%)"
    elif error_rate < 0.10:
        quality = "Good (5-10%)"
    elif error_rate < 0.20:
        quality = "Acceptable (10-20%)"
    else:
        quality = "Poor (> 20%) -- may indicate audio quality issues or heavy jargon"

    print(f"Quality assessment:     {quality}")

    print("\n" + "=" * 60)
    print("NORMALIZED TEXT USED FOR WER COMPARISON")
    print("=" * 60)
    print(f"\nOFFICIAL (first 1000 chars):")
    print(wrap(official_norm[:1000], indent=""))
    print(f"\nWHISPER (first 1000 chars):")
    print(wrap(whisper_norm[:1000], indent=""))

    diffs = get_aligned_differences(official_norm, whisper_norm)

    print("\n" + "=" * 60)
    print("ALIGNED DIFFERENCES (first 5, via difflib sequence matching)")
    print("=" * 60)
    if not diffs:
        print("No differences found.")
    for i, diff in enumerate(diffs[:5], 1):
        print(f"\n[{i}]")
        if diff["official"]:
            print(wrap(f"OFFICIAL: {diff['official']}", indent="  "))
        if diff["whisper"]:
            print(wrap(f"WHISPER:  {diff['whisper']}", indent="  "))

    print("\n" + "=" * 60)

    # Save full report to file
    report_path = whisper_path.parent / f"{whisper_path.stem}_wer_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"WER: {error_rate * 100:.1f}%\n")
        f.write(f"Quality: {quality}\n")
        f.write(f"Official word count: {ref_word_count}\n")
        f.write(f"Whisper word count: {hyp_word_count}\n\n")
        f.write("NORMALIZED TEXT USED FOR WER COMPARISON\n")
        f.write("=" * 60 + "\n")
        f.write(f"OFFICIAL (first 1000 chars):\n")
        f.write(textwrap.fill(official_norm[:1000], width=WRAP_WIDTH) + "\n\n")
        f.write(f"WHISPER (first 1000 chars):\n")
        f.write(textwrap.fill(whisper_norm[:1000], width=WRAP_WIDTH) + "\n\n")
        f.write(f"ALIGNED DIFFERENCES (all {len(diffs)}, via difflib sequence matching):\n")
        f.write("=" * 60 + "\n")
        for i, diff in enumerate(diffs, 1):
            f.write(f"\n[{i}]\n")
            if diff["official"]:
                f.write(textwrap.fill(f"OFFICIAL: {diff['official']}",
                                      width=WRAP_WIDTH, initial_indent="  ",
                                      subsequent_indent="  ") + "\n")
            if diff["whisper"]:
                f.write(textwrap.fill(f"WHISPER:  {diff['whisper']}",
                                      width=WRAP_WIDTH, initial_indent="  ",
                                      subsequent_indent="  ") + "\n")

    print(f"Report saved to: {report_path}")
    return error_rate


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_transcripts.py <whisper_txt> <official_pdf>")
        print("Example: python compare_transcripts.py samples/6-19/whisper-output/google-q1-2026.txt samples/6-19/google-q1-2026.pdf")
        sys.exit(1)

    compare(sys.argv[1], sys.argv[2])