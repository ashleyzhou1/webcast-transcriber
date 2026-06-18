"""
transcribe.py

Takes a local audio file (mp3, wav, etc.) and returns a transcript using
OpenAI's open-source Whisper model, running entirely locally (no API key,
no per-minute cost).

Usage (standalone):
    python transcribe.py path/to/audio.mp3

Usage (as a module):
    from transcribe import transcribe_audio
    result = transcribe_audio("path/to/audio.mp3", model_size="base")
"""

import sys
import time
import json
from pathlib import Path

import whisper


def transcribe_audio(audio_path: str, model_size: str = "base") -> dict:
    """
    Transcribe a local audio file using Whisper.

    Args:
        audio_path: path to the audio file (mp3, wav, m4a, etc.)
        model_size: one of "tiny", "base", "small", "medium", "large",
                    or their English-only variants "tiny.en", "base.en",
                    "small.en", "medium.en". Bigger = more accurate but
                    slower. For English-language content (like a US
                    company's earnings call), the .en variants are
                    slightly more accurate and just as fast as their
                    multilingual counterparts. "base.en" is a good
                    default for a quick POC; "small.en" or "medium.en"
                    for better accuracy once quality matters more.

    Returns:
        dict with keys: text (full transcript), segments (timestamped
        chunks), language (detected language), duration_seconds (how
        long transcription took), model_size
    """
    audio_path = str(audio_path)
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)

    print(f"Transcribing {audio_path} (this may take a while for long audio)...")
    start = time.time()
    result = model.transcribe(audio_path, verbose=False)
    elapsed = time.time() - start

    return {
        "text": result["text"].strip(),
        "segments": result["segments"],
        "language": result.get("language"),
        "duration_seconds": round(elapsed, 1),
        "model_size": model_size,
    }


def save_transcript(result: dict, output_path: str):
    """Save transcript to disk: a readable, paragraph-broken .txt (with
    timestamps) and a .json file (full result with raw text + segments)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Readable .txt: broken into paragraphs every ~6 segments, with
    # timestamps, so a human can skim it and jump to a moment in the audio
    txt_path = output_path.with_suffix(".txt")
    lines = []
    segments = result.get("segments", [])
    for i, seg in enumerate(segments):
        minutes = int(seg["start"] // 60)
        seconds = int(seg["start"] % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg['text'].strip()}")
        # insert a blank line every 6 segments to create paragraph breaks
        if (i + 1) % 6 == 0:
            lines.append("")
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    # JSON: full result, including the raw flat "text" field (useful for
    # database storage later) plus segments/timestamps/metadata
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Saved readable transcript (with timestamps) to: {txt_path}")
    print(f"Saved full result (with segments/timestamps) to: {json_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_path> [model_size] [output_dir]")
        sys.exit(1)

    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base.en"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "../samples"

    result = transcribe_audio(audio_file, model_size=model_size)

    print("\n--- TRANSCRIPT PREVIEW (first 500 chars) ---")
    print(result["text"][:500])
    print(f"\n[Transcription took {result['duration_seconds']}s using '{model_size}' model]")

    out_name = Path(audio_file).stem
    save_transcript(result, f"{output_dir}/{out_name}")