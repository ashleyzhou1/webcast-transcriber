# Webcast Transcription - Findings Log

**Audio/video sample files:** not included in this repo (too large for GitHub).
Full set of files available in the [project Google Drive](https://drive.google.com/drive/folders/17D9ajhhCqGy4qU3mu6fG-iW5j5QBlE0b?usp=sharing).

## June 17–18, 2026

**Goal:** Explore feasibility of automatically transcribing company webcasts (earnings calls, announcements) for display in the app. Initial scope: manual link discovery → automated download and transcription, starting with large-cap companies.

---

## 1. Download + Transcribe/Extract Pipeline

### Scripts Built

- **`src/download.py`** — given a direct URL (mp3, mp4, wav, m4a, pdf), downloads the file locally. If mp4, automatically extracts audio via ffmpeg. Handles signed/authenticated CDN URLs (e.g. Microsoft's Azure CDN links with expiry parameters).
- **`src/transcribe.py`** — given a local audio file, transcribes it using OpenAI's open-source Whisper model (runs entirely locally, no API key, no cost). Outputs a readable timestamped `.txt` and a `.json` with full segment/metadata detail.
- **`src/extract_pdf.py`** — given a local PDF, extracts plain text directly (no AI/ML needed for text-based PDFs). Outputs `.txt` and `.json`, matching the same format as transcribe.py for consistency.

### Dependencies

All dependencies listed in `requirements.txt`. Key ones:
- `openai-whisper` — local speech-to-text model
- `requests`, `beautifulsoup4` — download and scraping
- `pypdf` — PDF text extraction
- `ffmpeg` — audio decoding (system install, not pip)

### Pipeline Commands Used (tested and working)

**Amazon — download + transcribe:**
```bash
python download.py "https://s2.q4cdn.com/299287126/files/doc_earnings/2026/q1/generic/Amazon-Quarterly-Earnings-Report-Q1-2026-Full-Call.mp3" "samples/Audio-Video"
python transcribe.py "samples/Audio-Video/Amazon-Quarterly-Earnings-Report-Q1-2026-Full-Call.mp3" base.en "samples/transcripts/whisper-or-extracted"
```

**Microsoft — download + transcribe (mp4, audio extracted automatically):**
```bash
python download.py "https://mediusdl.event.microsoft.com/video-7533932/a4a066b001/VOD001.mp4?..." "samples/Audio-Video"
python transcribe.py "samples/Audio-Video/VOD001.mp3" base.en "samples/transcripts/whisper-or-extracted"
```

### Results

All pipelines ran successfully and produced `.txt` (human-readable) and `.json` (structured, suitable for database storage).

**Key limitation:** pipeline only works when you already have a direct download link.

---

## 2. ChatGPT Search + Web Scraper (Link Discovery)

### Motivation

The pipeline above requires a direct download URL as input. This section documents two approaches tested to find those URLs automatically.

### Approach A: ChatGPT Search

Used a structured prompt against Amazon, Microsoft, Apple, and HP Inc. to search their IR pages and return downloadable file links as JSON. Raw outputs saved to: `research/6-17/llm-search-results/`

### Approach B: Web Scraper (`src/scrape_ir_page.py`)

Scraper fetches an IR page's HTML and keyword-matches links against terms like "webcast", "earnings call", "replay", "conference call". Raw outputs saved to: `research/6-17/scraper-results/`

### Results

| Company | ChatGPT | Scraper | Direct audio found? |
|---|---|---|---|
| Amazon | Generic IR landing page only | 0 results | No |
| Apple | Generic streaming page only | 0 results | No |
| HP Inc. | Generic IR page + 1 PDF | 169 results, 2 PDFs | No |
| Microsoft | Same page URL repeated | A few results, 0 direct files | No |

Neither approach found a direct, downloadable audio file for any company.

---

## 3. Potential Idea: Quartr API + LLM API

Quartr is a financial data company with coverage of 15,000+ public companies. Their API provides live and archived earnings call audio, transcripts in JSON with speaker identification and timestamps, and filings as PDFs.

**Proposed pipeline:**
```
Quartr API → transcript JSON / audio URL
    → transcribe.py (if audio only) OR Quartr's own transcript
        → LLM API (Claude/ChatGPT) with transcript as context
            → structured output: summary, key metrics, sentiment
                → app database → app
```

---

## June 19–23, 2026

**Goal:** For each of the 20 Big Tech companies on the heatmap, download the webcast audio and find patterns/similarities across platforms.

### Company List (20)

- Amazon (AMZN), Microsoft (MSFT), Google (GOOG), Meta (META), Tesla (TSLA)
- Taiwan Semiconductor (TSM), Salesforce (CRM), SanDisk (SNDK), ASML (ASML)
- Broadcom (AVGO), Alibaba (BABA), Cisco (CSCO), Oracle (ORCL), AMD (AMD)
- Qualcomm (QCOM), IBM (IBM), Texas Instruments (TXN), Nvidia (NVDA)
- Apple (AAPL), Adobe (ADBE)

### Bottom Line

- Tesla, Google, and Adobe are hosted on YouTube — downloaded using `yt-dlp`. Adobe is on the Benzinga channel, not Adobe's official channel.
- Apple can't be completed because the recording is only available for ~2 weeks after it occurs. Next call expected late July 2026.
- Nvidia's quarterly earnings call is on Q4 Inc (same as Oracle, Meta, Cisco). A separate BofA conference keynote is on Veracast and requires a special segment-stitching workaround — see README.
- All other companies were handled by `save_login_session.py` + `find_media_url.py`, which automates finding the correct download link by watching page network traffic.
- 11/20 companies also had official transcript PDFs available: Google, Meta, TSMC, Salesforce, ASML, Alibaba, Cisco (prepared remarks only), AMD, Qualcomm, IBM, Adobe.

### `src/find_media_url.py` (Automated Link Finder)

Replaces the manual "open DevTools, watch network traffic, find the right URL" process. Opens the page, watches everything the page loads, and automatically picks out the real audio/video link using three patterns: a single repeated direct file, numbered HLS segments with a signed URL (Nvidia/Veracast case), or a streaming playlist (.m3u8). Full setup and run instructions in README.

### `src/download_hls_segments.py` (Signed Segment Stitcher)

Gets a signed URL signature from `find_media_url.py`, uses it to manually build a URL for each numbered segment, downloads each one, and runs ffmpeg to stitch them into a complete recording. Required for Veracast-hosted webcasts where ffmpeg drops the signature when following the manifest chain.

---

## June 23–26, 2026

**Goal:** Generate transcripts for all 19 companies, measure transcription quality, build a project spreadsheet, organize all outputs in Google Drive, and add speaker identification to transcripts.

---

### 4. Project Spreadsheet

A Google Sheets spreadsheet documents the full pipeline results across all 20 companies. Found in the [project Google Drive](https://drive.google.com/drive/folders/17D9ajhhCqGy4qU3mu6fG-iW5j5QBlE0b?usp=sharing) with two tabs:

**Tab 1 — Webcast Audio Coverage**
One row per company: platform, audio source URL, download method, file size, duration, whether assembly was required, whether an official PDF transcript exists, whether a Whisper transcript was generated, PDF source URL, and notes.

Columns: `company`, `ticker`, `platform`, `audio_source_url`, `download_method`, `file_size_mb`, `duration_min`, `required_assembly`, `has_official_pdf_transcript`, `whisper_transcript_generated`, `pdf_source_url`, `notes`

**Tab 2 — WER Comparison Results**
One row per company with an official PDF transcript (11 companies): WER score, quality assessment, word counts, and notes explaining any inflated scores.

Columns: `company`, `ticker`, `wer_percent`, `quality_assessment`, `official_word_count`, `whisper_word_count`, `notes`

---

### 5. Transcripts

**19 of 20 companies have a Whisper-generated transcript. Apple is the only exception (no audio available).**

All transcripts were generated using OpenAI's Whisper model (`base.en` for English calls, `base` for TSMC which is a mixed Mandarin/English call). Whisper runs entirely locally — no API key or cost required. Transcripts for companies that already had official PDFs were generated anyway for the quality comparison below.

All transcripts are in Google Drive under `transcripts/whisper-or-extracted/`.

---

### 6. Transcript Quality Comparison (WER)

For the 11 companies with official PDF transcripts, Whisper-generated transcripts were compared against the official versions using **Word Error Rate (WER)** — lower is better, 0% = perfect match. Both transcripts were normalized before comparison: timestamps stripped, lowercased, numbers converted to words, punctuation removed. Contractions kept as-is.

**Results:**

| Company | WER | Assessment |
|---|---|---|
| IBM | 10.1% | Good |
| Meta | 10.6% | Good |
| Google | 11.3% | Good |
| AMD | 12.8% | Good |
| Salesforce | 14.7% | Good |
| Adobe | 25.8% | See note |
| Qualcomm | 27.5% | See note |
| TSMC | 40.5% | See note |
| Alibaba | 63.5% | See note |
| Cisco | 155.9% | See note |
| ASML | 523.7% | See note |

**Key insight:** The 5 companies with clean apples-to-apples comparisons all scored 10–15% WER — consistent and acceptable for a local speech recognition model on clean English audio. The remaining 6 high scores reflect document mismatches, not bad transcription:

- **ASML**: PDF is a short 3-question interview (1,693 words); Whisper transcript is the full 60-minute call (9,437 words) — completely different documents.
- **Cisco**: PDF is prepared remarks only, not the full call.
- **Qualcomm, Alibaba, Adobe**: PDFs have large FactSet/LSEG metadata headers inflating the official word count.
- **TSMC**: Mixed Mandarin/English call; PDF is English-only translation.

Full WER reports are in Google Drive under `transcripts/wer-reports/` and summarized in the project spreadsheet.

---

### 7. Speaker Identification

Speaker labels were added to all 19 Whisper transcripts using the Anthropic API (Claude Sonnet). Each transcript was sent to Claude with a prompt instructing it to use web search to look up the company's executive roster and analyst participants, identify speaker transitions from context clues, and insert labels in the format `[SPEAKER NAME - ROLE]:`.

Claude also corrects obvious Whisper name transcription errors in the labels (e.g. Whisper's "Cinder Pichai" → `[SUNDAR PICHAI - CEO & DIRECTOR, ALPHABET/GOOGLE]:`). Tested and verified manually against the AMD official PDF transcript — all 13 speakers correctly identified.

Diarized transcripts saved as `<company>_diarized.txt` in Google Drive under `transcripts/diarized/`.

---

### 8. Google Drive Organization

All files are in the [project Google Drive](https://drive.google.com/drive/folders/17D9ajhhCqGy4qU3mu6fG-iW5j5QBlE0b?usp=sharing):

webcast-transcriber/
├── Audio-Video/               ← all mp3 and mp4 files (19 companies)
├── transcripts/
│   ├── whisper-or-extracted/  ← Whisper-generated .txt and .json files
│   ├── official-pdfs/         ← company-published PDF transcripts (11 companies)
│   ├── diarized/              ← speaker-labeled transcripts (_diarized.txt = primary; _diarized_ts.txt = timestamped version for web player)
│   ├── clean/                 ← cleaned transcripts with timestamps and boilerplate removed
│   └── wer-reports/           ← WER comparison reports for 11 companies
└── Webcast Audio Coverage     ← project spreadsheet

Audio and video files are not committed to the GitHub repo (too large). All text outputs are in both the repo under `samples/` and in Google Drive.

## June 26 - July 1, 2026
### 9. Transcript Cleanup

A cleanup script (`src/clean_transcripts.py`) post-processes the diarized transcripts:
- Strips the Claude API preamble (speaker roster summary generated before the transcript)
- Removes timestamps
- Joins fragmented lines into paragraphs (~10 sentences each)
- Preserves speaker labels in `[SPEAKER NAME - ROLE]:` format

Cleaned transcripts saved to `samples/transcripts/clean/`.

### 10. Timestamped Diarized Transcripts

For companies where the diarized transcript was initially generated from a PDF-extracted source (no timestamps), a second diarized version was generated using the Whisper audio transcript as input instead. These are saved with a `_diarized_ts.txt` suffix in `samples/transcripts/diarized/` to distinguish them from the original `_diarized.txt` versions.

The `_ts` versions are used by the web caption player.

Companies with both versions: alibaba, amd, asml, cisco, ibm, meta, qualcomm, salesforce, ti, tsmc.

### 11. Audio Caption Web Player

Built a browser-based audio player that plays earnings call recordings with real-time captions and speaker labels for all 19 companies.

**How it works:**

Python preprocessing (run once):
- `src/build_caption_data.py` — converts Whisper JSON files into `{start, end, text, speaker}`
- `src/add_speakers.py` — merges speaker labels from diarized transcripts into the caption JSONs

Web player (`web/index.html`) is a single HTML/CSS/JavaScript file.

**Features:**
- Dropdown to select any of the 19 companies
- Real-time captions synced to audio, with speaker names
- Playback speed control: 1× / 1.25× / 1.5× / 2×

**To run:**
```bash
python src/build_caption_data.py   # one-time setup
python src/add_speakers.py         # one-time setup
python -m http.server 8000         # from repo root
# then open http://localhost:8000/web/ in Chrome
```
## July 1–6, 2026

**Tasks:** Implemented Additional Features:
- Release date and fiscal quarter label under title
- Full transcript modal with language-aware translation
- Live captions and audio in selected language

---

### Audio Caption Web Player (Extended)

Built on top of the basic caption player from the previous session. Full feature set:

- **Company info bar** — fiscal quarter and release date displayed under the title when a company is selected
- **Full transcript modal** — button opens a popup with the complete transcript; translates to selected language
- **Language dropdown** — 8 languages supported: English, Chinese (Simplified), Spanish, French, Japanese, Korean, Arabic, German
- **Translated audio (TTS)** — when a non-English language is selected, the original mp3 is replaced by browser Text-to-Speech (`speechSynthesis` Web API). Each segment is spoken as it appears, chained sequentially. Male/female voice selected per segment based on speaker.
- **Audio seeking** — switched from `python -m http.server` to Flask (`web/serve.py`) because Python's basic server doesn't support HTTP range requests, which are required for the browser to seek within large mp3 files
- **Skip buttons** — skip ±15 seconds in English mode, ±5 segments in TTS mode

To run:
```bash
python web/serve.py
# open http://127.0.0.1:8000
```