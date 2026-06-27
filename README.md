# webcast-transcriber

A Python pipeline for downloading, transcribing, and extracting text from company earnings call webcasts and press releases.

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
│   └── test_all_companies.sh
├── research/                     # Findings log and research outputs
│   ├── mobile-mockup.png         # Mockup for audio player feature  
│   ├── findings.md
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
│   ├── index.html
│   └── data/                     # Preprocessed caption JSONs (one per company)
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

`translate.py` additionally requires a Google Cloud API key (free tier:
500K characters/month):
```bash
export GOOGLE_TRANSLATE_API_KEY="your-key-here"
```

`diarize.py` requires an Anthropic API key:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

---

## Scripts

**`src/download.py`** — download a direct audio, video, or PDF URL locally. Video files are automatically converted to mp3 via ffmpeg.
```bash
python download.py <url> [output_dir]
```

**`src/transcribe.py`** — transcribe a local audio file using Whisper (runs locally, no API key needed). Use `base.en` for English, `base` for mixed-language calls.
```bash
python transcribe.py <audio_path> [model_size] [output_dir]
```

**`src/extract_pdf.py`** — extract plain text from a local PDF file.
```bash
python extract_pdf.py <pdf_path> [output_dir]
```

**`src/compare_transcripts.py`** — compare a Whisper transcript against an official PDF using Word Error Rate (WER).
```bash
python src/compare_transcripts.py <whisper_txt> <official_pdf>
```

**`src/diarize.py`** — add speaker labels to a Whisper transcript using the Anthropic API (Claude Sonnet with web search).
```bash
python src/diarize.py <company> [company2] ...
```

**`src/translate.py`** — translate a transcript into another language using the Google Translate API.
```bash
python translate.py <text_file> <target_lang_code> [output_dir]
# Example: python translate.py samples/transcripts/whisper-or-extracted/oracle-q4-fy2026.txt zh samples/transcripts/whisper-or-extracted
```

**`src/scrape_ir_page.py`** — scrape a company IR page for webcast-related links and save results as JSON.
```bash
python scrape_ir_page.py <ir_page_url> <company_name> <ticker> [output_path]
```

**`src/clean_transcripts.py`** — removes timestamps, boilerplate preamble, and reformats diarized transcripts into readable paragraphs. Saves to `samples/transcripts/clean/`.
```bash
python src/clean_transcripts.py --all        # all 19 companies
python src/clean_transcripts.py amd google   # specific companies
```

**`src/build_caption_data.py`** — preprocesses Whisper JSON files into lean `{start, end, text}` caption JSONs for the web player. Saves to `web/data/`.
```bash
python src/build_caption_data.py   # all 19 companies
```
**`src/build_caption_data.py`** — preprocesses Whisper JSON files into lean caption JSONs for the web player. Saves to `web/data/`.
```bash
python src/build_caption_data.py
```

**`src/add_speakers.py`** — merges speaker labels from diarized transcripts into caption JSONs. Uses timestamp alignment or fuzzy text matching depending on available diarized file.
```bash
python src/add_speakers.py
```

**`src/clean_transcripts.py`** — strips timestamps and boilerplate from diarized transcripts and reformats into readable paragraphs. Saves to `samples/transcripts/clean/`.
```bash
python src/clean_transcripts.py --all
```

> **Note:** scripts default to writing output to `../samples`. Pass an output directory explicitly if running from a different location.

---

## Finding & Downloading Webcast Audio/Video

### find_media_url.py

Given a webcast page URL, automatically finds the downloadable audio/video link by watching the page's network traffic (replaces manual browser DevTools inspection). It looks for one of three patterns, in priority order:

1. **A direct media file** (same file requested multiple times with "206 Partial Content" status) → hands off to `download.py`
2. **Numbered HLS segments with a signed URL** (e.g. `..._00001.ts`, `..._00002.ts`) → hands off to `download_hls_segments.py` (see Nvidia section below)
3. **A streaming playlist file** (`.m3u8`) → hands off to `ffmpeg`, which fetches and reassembles the full stream directly

```bash
python find_media_url.py <webcast_page_url> [session_file.json] [--debug]
```

`--debug` is required to allow the user to manually click play.

### Step 1: Save a login session (one-time per platform)

Login once per platform. This login info is saved to a JSON file. Log in manually, then press Enter.

```bash
python src/save_login_session.py "<a login page URL on that platform>" "<platform>_session.json"
```

**Important:** If `find_media_url.py` opens to a login screen instead of the webcast, log in again manually in that window (just means the saved session timed out on the browser's end).

### Batch testing multiple companies (test_all_companies.sh)

To run the link-finding process across many companies in one sitting, edit the `COMPANIES` list near the top of `src/test_all_companies.sh`:

```bash
COMPANIES=(
  "company_name|https://webcast-page-url-here.com"
  "another_company|https://another-url-here.com"
)
```

Run it with:
```bash
bash src/test_all_companies.sh
```

The script automatically downloads/converts each result to mp3 and saves it to the output folder set at the top of the script.

### YouTube-hosted webcasts (Tesla, Google/Alphabet, Adobe)

For YouTube-hosted webcasts, use `yt-dlp`:
```bash
pip install yt-dlp
```
```bash
yt-dlp -x --audio-format mp3 -o "samples/Audio-Video/<company>.%(ext)s" "<youtube_watch_url>"
```

Examples:
```bash
yt-dlp -x --audio-format mp3 -o "samples/Audio-Video/tesla-q1-2026.%(ext)s" "https://www.youtube.com/watch?v=qO7T5zgRvXM"
yt-dlp -x --audio-format mp3 -o "samples/Audio-Video/google-q1-2026.%(ext)s" "https://www.youtube.com/watch?v=LPJoiDiVkTI"
yt-dlp -x --audio-format mp3 -o "samples/Audio-Video/adobe-q2-fy26.%(ext)s" "https://www.youtube.com/watch?v=hhtVWLMpYic"
```

---

## Nvidia (Special Case): Signed HLS Segments

Nvidia's quarterly earnings call is on Q4 Inc (same as Oracle, Meta, Cisco) and downloads as a standard direct mp4. However, Nvidia also appeared at the BofA Global Tech conference hosted on Veracast, which requires a different workaround.

Veracast breaks the video into numbered chunks (e.g. `..._00001.ts` through `..._00175.ts`), each requiring a signed permission token. ffmpeg can read the `.m3u8` manifest but does NOT carry that signature forward when fetching individual chunks — causing 403 errors on every segment. The fix: download each chunk directly with the signature manually re-attached, then stitch them together.

**Process:**

1. Run `find_media_url.py` on the Veracast page — it detects the numbered-segment pattern and prints a ready-to-fill command, missing only the segment count.

2. Find the total segment count:
```bash
curl -s "<m3u8_url_with_query_string>" | tail -5
```
The last segment filename (e.g. `..._00175.ts`) tells you the total count.

3. Run the download:
```bash
python src/download_hls_segments.py \
  "<base_url_from_find_media_url_output>" \
  "<query_string_from_find_media_url_output>" \
  <num_segments> \
  "samples/Audio-Video/nvidia-bofaconf.mp4" \
  1 <num_digits>
```

---

## Transcription

Use `base.en` for English calls, `base` for mixed-language calls (e.g. TSMC):
```bash
python src/transcribe.py samples/Audio-Video/amd-q1-2026.mp3 base.en samples/transcripts/whisper-or-extracted
python src/transcribe.py samples/Audio-Video/tsmc-q1-2026.mp3 base samples/transcripts/whisper-or-extracted
```

Outputs a `.txt` (human-readable with timestamps) and `.json` (structured, suitable for database storage).

---

## Transcript Quality Comparison

Compares a Whisper transcript against an official PDF using Word Error Rate (WER):

```bash
python src/compare_transcripts.py "samples/transcripts/whisper-or-extracted/amd-q1-2026.txt" "samples/transcripts/official-pdfs/amd-q1-2026.pdf"
```

**Normalization applied before comparison:**
- Timestamps stripped
- Lowercased
- Numbers converted to words (`5` → `five`)
- Punctuation stripped
- Contractions kept as-is (`don't` ≠ `do not`)

Uses `difflib` sequence alignment to handle cases where the official PDF has extra boilerplate headers not present in the audio. Saves a full report to `samples/transcripts/wer-reports/`.

Requires:
```bash
pip install jiwer num2words cryptography
```

---

## Speaker Diarization

Adds speaker labels to Whisper transcripts using the Anthropic API (Claude Sonnet with web search):

```bash
export ANTHROPIC_API_KEY="your-key-here"
# Single company:
python src/diarize.py amd
# Batch:
python src/diarize.py amd ibm meta google oracle
```

Input: `samples/transcripts/whisper-or-extracted/<company>*.txt`
Output: `samples/transcripts/diarized/<company>_diarized.txt`

Labels use the format `[SPEAKER NAME - ROLE]:`. Claude uses web search to find the correct executive roster and corrects obvious Whisper name transcription errors in labels. TSMC (mixed Chinese/English) is handled automatically.

Requires:
```bash
pip install anthropic
```

---

## Google Drive

Audio/video files and all transcripts are stored in the [project Google Drive](https://drive.google.com/drive/folders/17D9ajhhCqGy4qU3mu6fG-iW5j5QBlE0b?usp=sharing), organized as follows:

```
webcast-transcriber/
├── Audio-Video/               ← all mp3 and mp4 files (19 companies)
├── transcripts/
│   ├── whisper-or-extracted/  ← Whisper .txt and .json outputs
│   ├── official-pdfs/         ← company-published PDF transcripts (11 companies)
│   ├── diarized/              ← speaker-labeled transcripts
│   └── wer-reports/           ← WER comparison reports
└── Webcast Audio Coverage     ← project spreadsheet (audio coverage + WER results)
```

Audio and video files are not committed to GitHub (too large). All text outputs are in both the repo under `samples/` and in Google Drive.

---
## Audio Caption Web Player

An in-browser audio player that plays earnings call recordings with real-time captions and speaker labels. Built as a local demo tool.

### How it works

**Python prepares the data (run once):**

`src/build_caption_data.py` converts the Whisper JSON files into lean caption JSONs containing only `{start, end, text}` per segment, saved to `web/data/`.

`src/add_speakers.py` adds a `speaker` field to each segment by cross-referencing the diarized transcripts. Uses timestamp alignment for companies with `_diarized_ts.txt`, fuzzy text matching for the rest. Updates `web/data/` in place.

`web/index.html` is a single self-contained HTML file with CSS (styling) and JavaScript (behavior) that loads the caption JSONs and mp3 files, syncs captions to audio playback in real time, and renders the scrollable transcript panel with speaker headers.

### Setup and run

```bash
# Step 1: build caption JSONs (only needed once, or after re-running diarization)
python src/build_caption_data.py
python src/add_speakers.py

# Step 2: start local server from repo root
python -m http.server 8000

# Step 3: open in Chrome
open http://localhost:8000/web/
```

### Features
- Dropdown to select any of the 19 companies
- Real-time captions synced to audio playback
- Speaker name displayed above each caption
- Playback speed: 1× / 1.25× / 1.5× / 2×
  
## Findings

See `research/findings.md` for full research notes, pipeline results, company-by-company coverage, transcript quality results, and proposed next steps.