"""
translate.py

Translates a transcript or extracted text file into a target language using
Helsinki-NLP's open-source translation models via HuggingFace Transformers.
Runs entirely locally — no API key, no cost. Models are downloaded once on
first use and cached automatically.

Models are language-pair specific. Supported target languages (from English):
    es  Spanish         Helsinki-NLP/opus-mt-en-es
    fr  French          Helsinki-NLP/opus-mt-en-fr
    de  German          Helsinki-NLP/opus-mt-en-de
    zh  Chinese         Helsinki-NLP/opus-mt-en-zh
    ja  Japanese        Helsinki-NLP/opus-mt-en-jap
    ko  Korean          Helsinki-NLP/opus-mt-en-ko
    pt  Portuguese      Helsinki-NLP/opus-mt-en-pt
    ar  Arabic          Helsinki-NLP/opus-mt-en-ar
    hi  Hindi           Helsinki-NLP/opus-mt-en-hi
    it  Italian         Helsinki-NLP/opus-mt-en-it

Usage (standalone):
    python translate.py <text_file> <target_language_code> [output_dir]

    Example:
    python translate.py "../samples/6-17/hp-q2-2026.txt" es "../samples/6-17"

Usage (as a module):
    from translate import translate_text
    result = translate_text("Hello world", target_lang="fr")
"""

import sys
import json
import time
from pathlib import Path

from transformers import MarianMTModel, MarianTokenizer

# Mapping of language codes to Helsinki-NLP model names
LANGUAGE_MODELS = {
    "es": "Helsinki-NLP/opus-mt-en-es",
    "fr": "Helsinki-NLP/opus-mt-en-fr",
    "de": "Helsinki-NLP/opus-mt-en-de",
    "zh": "Helsinki-NLP/opus-mt-en-zh",
    "ja": "Helsinki-NLP/opus-mt-en-jap",
    "ko": "Helsinki-NLP/opus-mt-en-ko",
    "pt": "Helsinki-NLP/opus-mt-en-pt",
    "ar": "Helsinki-NLP/opus-mt-en-ar",
    "hi": "Helsinki-NLP/opus-mt-en-hi",
    "it": "Helsinki-NLP/opus-mt-en-it",
}

# Max tokens per chunk — Marian models have a 512-token limit per input.
# We split text into chunks to handle long transcripts safely.
MAX_CHUNK_CHARS = 1000


def _chunk_text(text: str, chunk_size: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split text into chunks at paragraph/sentence boundaries to avoid
    cutting mid-sentence when feeding to the model."""
    paragraphs = text.split("\n")
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += para + "\n"
        else:
            if current:
                chunks.append(current.strip())
            current = para + "\n"

    if current:
        chunks.append(current.strip())

    return chunks


def translate_text(text: str, target_lang: str) -> str:
    """
    Translate a string of English text into the target language.

    Args:
        text: English text to translate
        target_lang: ISO 639-1 language code (e.g. "es", "fr", "zh")

    Returns:
        Translated text as a single string.
    """
    if target_lang not in LANGUAGE_MODELS:
        supported = ", ".join(sorted(LANGUAGE_MODELS.keys()))
        raise ValueError(
            f"Unsupported target language: '{target_lang}'. "
            f"Supported codes: {supported}"
        )

    model_name = LANGUAGE_MODELS[target_lang]
    print(f"Loading translation model '{model_name}'...")
    print("(Model will be downloaded on first use — this may take a minute.)")

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    chunks = _chunk_text(text)
    translated_chunks = []

    print(f"Translating {len(chunks)} chunk(s)...")
    for i, chunk in enumerate(chunks, 1):
        inputs = tokenizer(
            [chunk],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        outputs = model.generate(**inputs)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        translated_chunks.append(translated)
        if i % 10 == 0:
            print(f"  {i}/{len(chunks)} chunks done...")

    return "\n".join(translated_chunks)


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
    print(f"Translating '{input_path.name}' to '{target_lang}'...")

    start = time.time()
    translated = translate_text(text, target_lang=target_lang)
    elapsed = round(time.time() - start, 1)

    result = {
        "translated_text": translated,
        "target_lang": target_lang,
        "source_file": str(input_path),
        "duration_seconds": elapsed,
    }

    # Save output
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    txt_path = output_dir / f"{stem}_{target_lang}.txt"
    json_path = output_dir / f"{stem}_{target_lang}.json"

    txt_path.write_text(translated, encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved translated text to: {txt_path}")
    print(f"Saved metadata to: {json_path}")
    print(f"[Translation took {elapsed}s]")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python translate.py <text_file> <target_lang> [output_dir]")
        print("Example: python translate.py ../samples/6-17/hp-q2-2026.txt es ../samples/6-17")
        print(f"\nSupported language codes: {', '.join(sorted(LANGUAGE_MODELS.keys()))}")
        sys.exit(1)

    input_file = sys.argv[1]
    target_lang = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "../samples"

    result = translate_file(input_file, target_lang, output_dir)
    print(f"\n--- TRANSLATION PREVIEW (first 500 chars) ---")
    print(result["translated_text"][:500])