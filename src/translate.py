"""
translate.py

Translates a transcript or extracted text file into a target language using
the Google Cloud Translation API. Fast, accurate, supports 130+ languages.

Requires a Google Cloud API key with Cloud Translation API enabled.
Set your key as an environment variable before running:
    export GOOGLE_TRANSLATE_API_KEY="your-key-here"

Usage (standalone):
    python translate.py <text_file> <target_language_code> [output_dir]

    Example:
    python translate.py "../samples/6-17/amazon-q1-2026.txt" es "../samples/6-17"

Usage (as a module):
    from translate import translate_text
    result = translate_text("Hello world", target_lang="fr")
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

API_KEY = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


def translate_text(text: str, target_lang: str) -> str:
    """
    Translate a string of text into the target language using Google Translate.

    Args:
        text: text to translate (source language auto-detected)
        target_lang: ISO 639-1 language code (e.g. "es", "fr", "zh")

    Returns:
        Translated text as a string.
    """
    if not API_KEY:
        raise ValueError(
            "No API key found. Set your key with:\n"
            "export GOOGLE_TRANSLATE_API_KEY='your-key-here'"
        )

    response = requests.post(
        GOOGLE_TRANSLATE_URL,
        params={"key": API_KEY},
        json={
            "q": text,
            "target": target_lang,
            "format": "text",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]["translations"][0]["translatedText"]


def translate_file(
    input_path: str,
    target_lang: str,
    output_dir: str = "../samples",
) -> dict:
    """
    Translate a .txt transcript or extraction file into the target language.

    Returns a dict with: translated_text, target_lang, source_file,
    duration_seconds.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    text = input_path.read_text(encoding="utf-8")
    print(f"Translating '{input_path.name}' to '{target_lang}' via Google Translate...")

    start = time.time()
    translated = translate_text(text, target_lang=target_lang)
    elapsed = round(time.time() - start, 1)

    result = {
        "translated_text": translated,
        "target_lang": target_lang,
        "source_file": str(input_path),
        "duration_seconds": elapsed,
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    txt_path = output_dir / f"{stem}_{target_lang}.txt"
    json_path = output_dir / f"{stem}_{target_lang}.json"

    txt_path.write_text(translated, encoding="utf-8")
    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Saved translated text to: {txt_path}")
    print(f"Saved metadata to: {json_path}")
    print(f"[Translation took {elapsed}s]")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python translate.py <text_file> <target_lang> [output_dir]")
        print("Example: python translate.py ../samples/6-17/amazon-q1-2026.txt es ../samples/6-17")
        sys.exit(1)

    input_file = sys.argv[1]
    target_lang = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "../samples"

    result = translate_file(input_file, target_lang, output_dir)
    print(f"\n--- TRANSLATION PREVIEW (first 500 chars) ---")
    print(result["translated_text"][:500])