"""
add_speakers.py

Merges speaker labels from diarized transcripts into the caption JSON files
used by the web player. Adds a "speaker" field to each segment.

Two strategies depending on available diarized file:
  1. Timestamped (_diarized_ts.txt): parse speaker + timestamp, assign by time range
  2. Text-only (_diarized.txt): fuzzy text match to align speakers to segments

Input:  samples/transcripts/diarized/<company>_diarized_ts.txt (preferred)
        samples/transcripts/diarized/<company>_diarized.txt (fallback)
        web/data/<company>.json (caption segments)
Output: web/data/<company>.json (updated in place with "speaker" field)

Usage:
    python src/add_speakers.py           # all 19 companies
    python src/add_speakers.py amd       # single company
"""

import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

DIARIZED_DIR = Path("samples/transcripts/diarized")
CAPTION_DIR = Path("web/data")

COMPANIES = [
    "amazon", "adobe", "alibaba", "amd", "asml", "broadcom",
    "cisco", "google", "ibm", "meta", "microsoft", "nvidia",
    "oracle", "qualcomm", "salesforce", "sandisk", "tesla", "ti", "tsmc",
]

# Companies with _diarized_ts.txt (timestamped)
TS_COMPANIES = {
    "alibaba": "alibaba-q1-2026",
    "amd":     "amd-q1-2026",
    "asml":    "asml-q1-2026",
    "cisco":   "cisco-q2-2026",
    "ibm":     "ibm-q1-2026",
    "meta":    "meta-q1-2026",
    "qualcomm":"qualcomm-q2-2026",
    "salesforce": "salesforce-q1-fy27",
    "ti":      "ti-q3-2026",
    "tsmc":    "tsmc-q1-2026",
}

# Companies with only _diarized.txt (no timestamps)
TEXT_COMPANIES = {
    "amazon":    "Amazon-Quarterly-Earnings-Report-Q1-2026-Full-Call",
    "adobe":     "adobe-q2-fy26",
    "broadcom":  "broadcom-q1-2026",
    "google":    "google-q1-2026",
    "microsoft": "microsoft-q2-2026",
    "nvidia":    "nvidia-q1-fy27",
    "oracle":    "oracle-q4-fy2026",
    "sandisk":   "sandisk-q1-2026",
    "tesla":     "tesla-q1-2026",
}

SPEAKER_LABEL_RE = re.compile(r"^\[(.+?)\]:\s*$")
SPEAKER_INLINE_RE = re.compile(r"^\[(.+?)\]:\s*(.+)")
TIMESTAMP_RE = re.compile(r"^\[(\d{1,2}):(\d{2})\]")


def ts_to_seconds(m, s):
    return int(m) * 60 + int(s)


def clean_speaker(label):
    """Extract just the name+role from [NAME - ROLE]: format."""
    return label.strip("[]").rstrip(":")


def parse_ts_diarized(path):
    """
    Parse a _diarized_ts.txt file.
    Returns list of (start_seconds, speaker_label) sorted by time.
    """
    lines = path.read_text(encoding="utf-8").splitlines()

    # Find where transcript starts (skip Claude preamble)
    start_idx = 0
    for i, line in enumerate(lines):
        if SPEAKER_LABEL_RE.match(line.strip()) or SPEAKER_INLINE_RE.match(line.strip()):
            start_idx = i
            break
    lines = lines[start_idx:]

    speakers = []
    current_speaker = None
    current_start = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # New speaker label (standalone line)
        m_label = SPEAKER_LABEL_RE.match(line)
        if m_label:
            current_speaker = m_label.group(1).strip()
            current_start = None
            continue

        # Inline speaker + text
        m_inline = SPEAKER_INLINE_RE.match(line)
        if m_inline:
            current_speaker = m_inline.group(1).strip()
            current_start = None
            # Check if there's a timestamp in the rest
            rest = m_inline.group(2)
            m_ts = TIMESTAMP_RE.match(rest)
            if m_ts and current_speaker:
                t = ts_to_seconds(m_ts.group(1), m_ts.group(2))
                speakers.append((t, current_speaker))
                current_start = t
            continue

        # Timestamp line under current speaker
        m_ts = TIMESTAMP_RE.match(line)
        if m_ts and current_speaker and current_start is None:
            t = ts_to_seconds(m_ts.group(1), m_ts.group(2))
            speakers.append((t, current_speaker))
            current_start = t

    return speakers


def assign_speakers_by_time(segments, speaker_times):
    """
    For each segment, find which speaker was active at segment.start.
    speaker_times: list of (start_seconds, speaker_label) sorted by time.
    """
    if not speaker_times:
        return segments

    result = []
    for seg in segments:
        t = seg["start"]
        # Find last speaker whose start_time <= segment start
        active = speaker_times[0][1]
        for (ts, spk) in speaker_times:
            if ts <= t:
                active = spk
            else:
                break
        seg = dict(seg)
        seg["speaker"] = active
        result.append(seg)
    return result


def parse_text_diarized(path):
    """
    Parse a _diarized.txt file (no timestamps).
    Returns list of (speaker_label, text_block) in order.
    """
    lines = path.read_text(encoding="utf-8").splitlines()

    # Find where transcript starts
    start_idx = 0
    for i, line in enumerate(lines):
        if SPEAKER_LABEL_RE.match(line.strip()) or SPEAKER_INLINE_RE.match(line.strip()):
            start_idx = i
            break
    lines = lines[start_idx:]

    blocks = []
    current_speaker = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        m_label = SPEAKER_LABEL_RE.match(stripped)
        m_inline = SPEAKER_INLINE_RE.match(stripped)

        if m_label or m_inline:
            if current_speaker and current_lines:
                blocks.append((current_speaker, " ".join(current_lines)))
            if m_label:
                current_speaker = m_label.group(1).strip()
                current_lines = []
            else:
                current_speaker = m_inline.group(1).strip()
                rest = m_inline.group(2).strip()
                # Strip any timestamps from inline text
                rest = TIMESTAMP_RE.sub("", rest).strip()
                current_lines = [rest] if rest else []
        else:
            # Strip timestamps from content lines
            cleaned = TIMESTAMP_RE.sub("", stripped).strip()
            if cleaned:
                current_lines.append(cleaned)

    if current_speaker and current_lines:
        blocks.append((current_speaker, " ".join(current_lines)))

    return blocks


def normalize(text):
    """Normalize text for fuzzy matching."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def assign_speakers_by_text(segments, blocks):
    """
    Fuzzy match segment text to diarized blocks to find speaker.
    Builds a concatenated transcript from segments, then aligns blocks to it.
    """
    if not blocks:
        return segments

    # Build full segment text for matching
    seg_texts = [normalize(s["text"]) for s in segments]
    full_seg_text = " ".join(seg_texts)

    # For each block, find where in the full text it appears
    # Then map that position back to segment indices
    seg_lengths = [len(t) + 1 for t in seg_texts]  # +1 for space
    seg_starts = []
    pos = 0
    for l in seg_lengths:
        seg_starts.append(pos)
        pos += l

    # Find block boundaries in the full segment text
    block_seg_indices = []
    search_start = 0

    for speaker, block_text in blocks:
        norm_block = normalize(block_text)
        # Take first 60 chars of block for matching
        probe = norm_block[:60]
        if not probe:
            block_seg_indices.append((speaker, 0))
            continue

        best_ratio = 0
        best_pos = search_start
        # Search in a window
        window = full_seg_text[search_start:search_start + len(probe) * 8]
        for i in range(len(window) - len(probe) + 1):
            candidate = window[i:i + len(probe)]
            ratio = SequenceMatcher(None, probe, candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_pos = search_start + i

        # Convert char position to segment index
        seg_idx = 0
        for j, s in enumerate(seg_starts):
            if s <= best_pos:
                seg_idx = j
            else:
                break

        block_seg_indices.append((speaker, seg_idx))
        if best_ratio > 0.5:
            search_start = best_pos

    # Assign speakers to segments
    result = []
    for i, seg in enumerate(segments):
        active = block_seg_indices[0][0]
        for (spk, idx) in block_seg_indices:
            if idx <= i:
                active = spk
            else:
                break
        seg = dict(seg)
        seg["speaker"] = active
        result.append(seg)

    return result


def process(key):
    caption_path = CAPTION_DIR / f"{key}.json"
    if not caption_path.exists():
        raise FileNotFoundError(f"Caption JSON not found: {caption_path}")

    with open(caption_path, encoding="utf-8") as f:
        segments = json.load(f)

    # Try timestamped diarized first
    if key in TS_COMPANIES:
        stem = TS_COMPANIES[key]
        ts_path = DIARIZED_DIR / f"{stem}_diarized_ts.txt"
        if ts_path.exists():
            speaker_times = parse_ts_diarized(ts_path)
            segments = assign_speakers_by_time(segments, speaker_times)
            strategy = f"timestamp ({len(speaker_times)} speaker changes)"
        else:
            raise FileNotFoundError(f"Expected _diarized_ts.txt not found: {ts_path}")
    elif key in TEXT_COMPANIES:
        stem = TEXT_COMPANIES[key]
        txt_path = DIARIZED_DIR / f"{stem}_diarized.txt"
        if not txt_path.exists():
            # Try glob
            candidates = list(DIARIZED_DIR.glob(f"*{key}*_diarized.txt"))
            if not candidates:
                raise FileNotFoundError(f"No diarized file found for {key}")
            txt_path = candidates[0]
        blocks = parse_text_diarized(txt_path)
        segments = assign_speakers_by_text(segments, blocks)
        strategy = f"fuzzy text ({len(blocks)} speaker blocks)"
    else:
        raise ValueError(f"Unknown company: {key}")

    with open(caption_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False)

    # Verify
    speakers_found = len(set(s.get("speaker", "") for s in segments))
    print(f"  {key:12} → {strategy}, {speakers_found} unique speakers")


def main():
    args = sys.argv[1:]
    targets = args if args else COMPANIES

    print(f"Adding speakers to {len(targets)} caption file(s)...\n")
    success, failed = 0, []

    for key in targets:
        try:
            process(key)
            success += 1
        except Exception as e:
            print(f"  {key:12} ERROR: {e}")
            failed.append(key)

    print(f"\nDone. {success} succeeded, {len(failed)} failed.")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()