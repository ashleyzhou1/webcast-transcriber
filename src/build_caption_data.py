"""
build_caption_data.py

Preprocesses Whisper JSON files into lean caption JSON files for the web player.
Extracts only {start, end, text} per segment and saves to web/data/.

Input:  samples/transcripts/whisper-or-extracted/<company>.json
Output: web/data/<company-key>.json

Usage:
    python src/build_caption_data.py           # process all 19 companies
    python src/build_caption_data.py amd       # single company by key
"""

import json
import sys
from pathlib import Path

WHISPER_DIR = Path("samples/transcripts/whisper-or-extracted")
OUTPUT_DIR = Path("web/data")

# Map from short company key → Whisper JSON filename (stem only)
COMPANY_MAP = {
    "amazon":     "Amazon-Quarterly-Earnings-Report-Q1-2026-Full-Call",
    "adobe":      "adobe-q2-fy26",
    "alibaba":    "alibaba-q1-2026-audio",
    "amd":        "amd-q1-2026-audio",
    "asml":       "asml-q1-2026-audio",
    "broadcom":   "broadcom-q1-2026",
    "cisco":      "cisco-q2-2026-video",
    "google":     "google-q1-2026",
    "ibm":        "ibm-q1-2026-video",
    "meta":       "meta-q1-2026-video",
    "microsoft":  "microsoft-q2-2026",
    "nvidia":     "nvidia-q1-fy27",
    "oracle":     "oracle-q4-fy2026",
    "qualcomm":   "qualcomm-q2-2026-video",
    "salesforce": "salesforce-q1-fy27-video",
    "sandisk":    "sandisk-q1-2026",
    "tesla":      "tesla-q1-2026",
    "ti":         "ti-q3-2026-audio",
    "tsmc":       "tsmc-q1-2026-audio",
}


def process(key: str, stem: str) -> Path:
    source = WHISPER_DIR / f"{stem}.json"
    if not source.exists():
        raise FileNotFoundError(f"Whisper JSON not found: {source}")

    with open(source, encoding="utf-8") as f:
        data = json.load(f)

    if "segments" not in data:
        raise ValueError(f"No 'segments' key in {source} — may be a PDF extraction JSON")

    segments = [
        {
            "start": round(seg["start"], 2),
            "end":   round(seg["end"], 2),
            "text":  seg["text"].strip(),
        }
        for seg in data["segments"]
        if seg.get("text", "").strip()
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"{key}.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False)

    size_kb = output.stat().st_size // 1024
    print(f"  {key:12} → {output}  ({len(segments)} segments, {size_kb}KB)")
    return output


def main():
    args = sys.argv[1:]
    if args:
        targets = {k: COMPANY_MAP[k] for k in args if k in COMPANY_MAP}
        missing = [k for k in args if k not in COMPANY_MAP]
        if missing:
            print(f"Unknown company keys: {missing}")
            print(f"Valid keys: {list(COMPANY_MAP.keys())}")
    else:
        targets = COMPANY_MAP

    print(f"Building caption data for {len(targets)} company/companies...\n")
    success, failed = 0, []

    for key, stem in targets.items():
        try:
            process(key, stem)
            success += 1
        except Exception as e:
            print(f"  {key:12} ERROR: {e}")
            failed.append(key)

    print(f"\nDone. {success} succeeded, {len(failed)} failed.")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()