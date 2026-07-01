# webcast-transcriber

A Python pipeline for downloading, transcribing, and extracting text from company earnings call webcasts and press releases, with a browser-based audio player featuring real-time captions, speaker labels, and multi-language support.

---

## Project Structure

```
webcast-transcriber/
├── src/                          # Python scripts
│   ├── download.py
│   ├── transcribe.py
│   ├── extract_pdf.py
│   ├── scrape_ir_page.py
│   ├── translate.py
│   ├── find_media_url.py
│   ├── save_login_session.py
│   ├── download_hls_segments.py
│   ├── compare_transcripts.py
│   ├── diarize.py
│   ├── clean_transcripts.py
│   ├── build_caption_data.py
│   ├── add_speakers.py
│   └── test_all_companies.sh
├── research/                     # Findings log and research outputs
│   ├── findings.md
│   ├── mobile-mockup.png
│   └── 6-17/
│       ├── llm-search-results/
│       └── scraper-results/
├── samples/                      # Outputs (audio/video not included in repo)
│   ├── Audio-Video/
│   └── transcripts/
│       ├── whisper-or-extracted/
│       ├── official-pdfs/
│       ├── diarized/             # _diarized.txt = primary; _diarized_ts.txt = timestamped version for web player
│       ├── clean/
│       └── wer-reports/
├── web/                          # Audio caption web player
│   ├── index.html                ← single-file player (HTML + CSS + JS)
│   ├── serve.py                  ← Flask dev server (required for audio seeking)
│   ├── config.js                 ← API key config (gitignored, create manually)
│   └── data/                     ← preprocessed caption JSONs (one per company)
├── requirements.txt
└── README.md
```

---

## Setup

Requires Python 3.10+, pip, and ffmpeg.

```bash
git clone git@github.com:ashleyzhou1/webcast-transcriber.git
cd webcast-transcriber
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Install ffmpeg (Mac):
```bash
brew install ffmpeg
```

API keys required by certain scripts:

```bash
# Google Translate API (translate.py and web player translation features)
export GOOGLE_TRANSLATE_API_KEY="your-key-here"

# Anthropic API (diarize.py)
export ANTHROPIC_API_KEY="your-key-here"
```

Both keys can be added to `~/.zshrc` to persist across terminal sessions.

---

## Scripts

**`src/download.py`** — download a direct audio, video, or PDF URL locally. Video files are automatically converted to mp3 via ffmpeg.
```bash
python src/download.py <url> [output_dir]
```

**`src/transcribe.py`** — transcribe a local audio file using OpenAI Whisper (runs locally, no API key needed). Use `base.en` for English, `base` for mixed-language calls (e.g. TSMC).
```bash
python src/transcribe.py <audio_path> [model_size] [output_dir]
# English: python src/transcribe.py samples/Audio-Video/amd-q1-2026.mp3 base.en samples/transcripts/whisper-or-extracted
# Mixed:   python src/transcribe.py samples/Audio-Video/tsmc-q1-2026.mp3 base samples/transcripts/whisper-or-extracted
```

**`src/extract_pdf.py`** — extract plain text from a local PDF file.
```bash
python src/extract_pdf.py <pdf_path> [output_dir]
```

**`src/compare_transcripts.py`** — compare a Whisper transcript against an official PDF using Word Error Rate (WER). Normalizes both before comparison (strips timestamps, lowercases, converts numbers to words, strips punctuation). Saves a full report to `samples/transcripts/wer-reports/`.
```bash
python src/compare_transcripts.py <whisper_txt> <official_pdf>
# Example:
python src/compare_transcripts.py samples/transcripts/whisper-or-extracted/amd-q1-2026.txt samples/transcripts/official-pdfs/amd-q1-2026.pdf
```

**`src/diarize.py`** — add speaker labels to Whisper transcripts using the Anthropic API (Claude Sonnet with web search). Claude looks up the company's executive roster, identifies speaker transitions from context clues, and inserts labels in the format `[SPEAKER NAME - ROLE]:`. TSMC (mixed Chinese/English) is handled automatically. Output is saved to `samples/transcripts/diarized/`.
```bash
python src/diarize.py <company> [company2] ...
# Single:  python src/diarize.py amd
# Batch:   python src/diarize.py amd ibm meta google oracle
```

**`src/clean_transcripts.py`** — strips Claude API preamble, removes timestamps, and reformats diarized transcripts into readable paragraphs (~10 sentences each). Preserves speaker labels. Saves to `samples/transcripts/clean/`.
```bash
python src/clean_transcripts.py --all          # all 19 companies
python src/clean_transcripts.py amd google     # specific companies
```

**`src/build_caption_data.py`** — preprocesses Whisper JSON files into lean `{start, end, text}` caption JSONs for the web player. Saves to `web/data/`.
```bash
python src/build_caption_data.py               # all 19 companies
python src/build_caption_data.py amd           # single company
```

**`src/add_speakers.py`** — merges speaker labels from diarized transcripts into the caption JSONs in `web/data/`. Uses timestamp alignment for companies with `_diarized_ts.txt`, fuzzy text matching for the rest. Updates JSON files in place.
```bash
python src/add_speakers.py                     # all 19 companies
python src/add_speakers.py amd                 # single company
```

**`src/translate.py`** — translate a transcript file into another language using the Google Translate API. Requires `GOOGLE_TRANSLATE_API_KEY`.
```bash
python src/translate.py <text_file> <target_lang_code> [output_dir]
# Example: python src/translate.py samples/transcripts/whisper-or-extracted/oracle-q4-fy2026.txt zh samples/transcripts/whisper-or-extracted
```

**`src/scrape_ir_page.py`** — scrape a company IR page for webcast-related links and save results as JSON.
```bash
python src/scrape_ir_page.py <ir_page_url> <company_name> <ticker> [output_path]
```

> **Note:** scripts default to writing output to `../samples`. Pass an output directory explicitly if running from a different location.

---

## Finding & Downloading Webcast Audio/Video

### find_media_url.py

Given a webcast page URL, automatically finds the downloadable audio/video link by watching the page's network traffic. It looks for one of three patterns, in priority order:

1. **A direct media file** (same file requested multiple times with "206 Partial Content" status) → hands off to `download.py`
2. **Numbered HLS segments with a signed URL** (e.g. `..._00001.ts`, `..._00002.ts`) → hands off to `download_hls_segments.py`
3. **A streaming playlist file** (`.m3u8`) → hands off to `ffmpeg`, which fetches and reassembles the full stream directly

```bash
python src/find_media_url.py <webcast_page_url> [session_file.json] [--debug]
```

`--debug` is required to allow the user to manually click play on the page.

### Step 1: Save a login session (one-time per platform)

```bash
python src/save_login_session.py "<login_page_url>" "<platform>_session.json"
```

Log in manually in the browser window that opens, then press Enter. Session files are gitignored.

### Batch testing multiple companies

Edit the `COMPANIES` list in `src/test_all_companies.sh` then run:
```bash
bash src/test_all_companies.sh
```

### YouTube-hosted webcasts (Tesla, Google/Alphabet, Adobe)

```bash
pip install yt-dlp
yt-dlp -x --audio-format mp3 -o "samples/Audio-Video/tesla-q1-2026.%(ext)s" "https://www.youtube.com/watch?v=qO7T5zgRvXM"
yt-dlp -x --audio-format mp3 -o "samples/Audio-Video/google-q1-2026.%(ext)s" "https://www.youtube.com/watch?v=LPJoiDiVkTI"
yt-dlp -x --audio-format mp3 -o "samples/Audio-Video/adobe-q2-fy26.%(ext)s" "https://www.youtube.com/watch?v=hhtVWLMpYic"
```

---

## Nvidia (Special Case): Signed HLS Segments

Nvidia's quarterly earnings call is on Q4 Inc and downloads as a standard direct mp4. However, a separate BofA conference keynote is on Veracast, which breaks the video into numbered chunks each requiring a signed permission token. ffmpeg drops the signature when following the manifest chain, so each chunk must be downloaded manually.

1. Run `find_media_url.py` — it detects the pattern and prints a ready-to-fill command.
2. Find the total segment count: `curl -s "<m3u8_url>" | tail -5`
3. Run:
```bash
python src/download_hls_segments.py \
  "<base_url>" "<query_string>" <num_segments> \
  "samples/Audio-Video/nvidia-bofaconf.mp4" 1 <num_digits>
```

---

## Audio Caption Web Player

A browser-based player for all 19 earnings call recordings with real-time captions, speaker labels, multi-language support, and translated audio playback.

### Prerequisites

**1. Create `web/config.js` (gitignored — never committed):**
```bash
echo 'const GOOGLE_TRANSLATE_API_KEY = "your-key-here";' > web/config.js
```

**2. Build caption data (run once, or after re-running diarization):**
```bash
python src/build_caption_data.py
python src/add_speakers.py
```

**3. Install Flask (required for audio seeking support):**
```bash
pip install flask
```

### Running the player

```bash
python web/serve.py
# then open http://127.0.0.1:8000 in Chrome
```

### Features

**Playback (English mode)**
- Company dropdown
- Real-time captions
- Speaker name displayed above each caption in the format `[SPEAKER NAME - ROLE]`
- Playback speed: 1× / 1.25× / 1.5× / 2×

**Company info**
- Fiscal quarter and release date displayed under the title when a company is selected
- Full transcript button opens a modal with readable transcript

**Multi-language support**
- Language dropdown: English, Chinese (Simplified), Spanish, French, Japanese, Korean, Arabic, German
- Selecting a non-English language translates all caption segments
- Full transcript modal also translates when a non-English language is selected

**Translated audio (TTS mode)**
- When a non-English language is selected, audio switches from the original mp3 to browser-native Text-to-Speech (`speechSynthesis` Web API)
- Each caption segment is spoken aloud as it appears, chained via `utterance.onend` callbacks
- Male/female voice selection based on speaker

### How caption data is built

`build_caption_data.py` reads each company's Whisper JSON (which contains `{id, start, end, text, tokens, ...}` per segment) and strips it down to just `{start, end, text}`, saving to `web/data/<company>.json`.

`add_speakers.py` then adds a `speaker` field to each segment by cross-referencing the diarized transcripts:
- **Timestamp-based** (10 companies with `_diarized_ts.txt`): parses speaker label + first timestamp from each speaker block, assigns speaker to all Whisper segments within that time range
- **Fuzzy text matching** (9 companies with text-only `_diarized.txt`): takes the first 60 chars of each speaker block, uses `difflib.SequenceMatcher` to find the closest match in the concatenated Whisper text, maps that character position back to a segment index

---

## Google Drive

All audio/video files and transcripts are in the [project Google Drive](https://drive.google.com/drive/folders/17D9ajhhCqGy4qU3mu6fG-iW5j5QBlE0b?usp=sharing):

```
webcast-transcriber/
├── Audio-Video/               ← all mp3 and mp4 files (19 companies)
├── transcripts/
│   ├── whisper-or-extracted/  ← Whisper .txt and .json outputs
│   ├── official-pdfs/         ← company-published PDF transcripts (11 companies)
│   ├── diarized/              ← speaker-labeled transcripts
│   ├── clean/                 ← cleaned readable transcripts
│   └── wer-reports/           ← WER comparison reports
└── Webcast Audio Coverage     ← project spreadsheet (audio coverage + WER results)
```

Audio and video files are not committed to GitHub (too large). All text outputs are in both the repo and Google Drive.

---

## Findings

See `research/findings.md` for full research notes, pipeline results, company-by-company coverage, transcript quality results, and web player implementation details.