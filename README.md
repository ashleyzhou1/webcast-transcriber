# webcast-transcriber

A Python pipeline for downloading, transcribing, and extracting text from company earnings call webcasts and press releases.

---

## Project Structure

```
stockfan-webcast-transcriber/
├── src/                        # Python scripts
│   ├── download.py
│   ├── transcribe.py
│   ├── extract_pdf.py
│   ├── scrape_ir_page.py
│   └── translate.py
├── research/                   # Findings log and research outputs
│   ├── findings.md
│   └── 6-17/
│       ├── llm-search-results/
│       └── scraper-results/
├── samples/                    # Transcript outputs (audio/video not included)
│   └── 6-17/
├── requirements.txt
└── README.md
```

---

## Setup

Requires Python 3.10+, pip, and ffmpeg.

```bash
git clone git@github.com:ashleyzhou1/stockfan-webcast-transcriber.git
cd stockfan-webcast-transcriber
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install ffmpeg (Mac):

```bash
brew install ffmpeg
```

---

## Scripts

**`src/download.py`** — download a direct audio, video, or PDF URL locally. Video files are automatically converted to mp3 via ffmpeg.

```bash
python download.py <url> [output_dir]
```

**`src/transcribe.py`** — transcribe a local audio file using Whisper (runs locally, no API key needed).

```bash
python transcribe.py <audio_path> [model_size] [output_dir]
```

**`src/extract_pdf.py`** — extract plain text from a local PDF file.

```bash
python extract_pdf.py <pdf_path> [output_dir]
```

**`src/scrape_ir_page.py`** — scrape a company IR page for webcast-related links and save results as JSON.

```bash
python scrape_ir_page.py <ir_page_url> <company_name> <ticker> [output_path]
```
**`src/translate.py`** — translate a transcript or extracted text file into another language using the Google Translate API. Requires a Google Cloud API key (free tier: 500K characters/month, sufficient for most use cases).

```bash
export GOOGLE_TRANSLATE_API_KEY="your-key-here"
python translate.py <text_file> <target_lang_code> [output_dir]
# Example: python translate.py ../samples/6-17/amazon-q1-2026.txt zh ../samples/6-17
```

> **Note:** scripts default to writing output to `../samples`. Pass an output directory explicitly if running from a different location.

---

## Sample Files

Audio and video files are not included in this repo (too large for GitHub). Test files available here: [Google Drive link — add before sharing]

Transcript outputs (`.txt`, `.json`) for HP, Amazon, and Microsoft Q2 2026 earnings calls are included in `samples/6-17/`.

---

## Findings

See `research/findings.md` for full research notes, pipeline results, and the proposed next steps (Quartr API + LLM API architecture).