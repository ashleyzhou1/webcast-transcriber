# Webcast Transcription — Findings Log

**Audio/video sample files:** not included in this repo (too large for GitHub).
Full set of test files available [here](https://drive.google.com/drive/u/1/folders/17D9ajhhCqGy4qU3mu6fG-iW5j5QBlE0b)

## June 17–18, 2026

**Goal:** Explore feasibility of automatically transcribing company webcasts
(earnings calls, announcements) for display in the the app app. Initial
scope: manual link discovery → automated download and transcription,
starting with large-cap companies.

---

## 1. Download + Transcribe/Extract Pipeline

### Scripts Built

- **`src/download.py`** — given a direct URL (mp3, mp4, wav, m4a, pdf),
  downloads the file locally. If mp4, automatically extracts audio via
  ffmpeg. Handles signed/authenticated CDN URLs (e.g. Microsoft's Azure
  CDN links with expiry parameters).
- **`src/transcribe.py`** — given a local audio file, transcribes it using
  OpenAI's open-source Whisper model (runs entirely locally, no API key,
  no cost). Outputs a readable timestamped `.txt` and a `.json` with full
  segment/metadata detail.
- **`src/extract_pdf.py`** — given a local PDF, extracts plain text
  directly (no AI/ML needed for text-based PDFs). Outputs `.txt` and
  `.json`, matching the same format as transcribe.py for consistency.

### Dependencies

All dependencies listed in `requirements.txt`. Key ones:
- `openai-whisper` — local speech-to-text model
- `requests`, `beautifulsoup4` — download and scraping
- `pypdf` — PDF text extraction
- `ffmpeg` — audio decoding (system install, not pip)

To set up and run:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg        # Mac
```

### Pipeline Commands Used (tested and working)

**HP PDF — download + extract:**
```bash
python download.py "https://www.hp.com/content/dam/sites/garage-press/press/press-releases/2026/q2-fy26-earnings/HP_Inc_Reports_Q2_FY26_Earnings.pdf" "../samples/6-17"
python extract_pdf.py "../samples/6-17/HP_Inc_Reports_Q2_FY26_Earnings.pdf" "../samples/6-17"
```

**HP audio — download + transcribe:**
```bash
python download.py "https://78449.choruscall.com/dataconf/productusers/hpe/media/2026/hpe260601_1700_28016_archive.mp3" "../samples/6-17"
python transcribe.py "../samples/6-17/hpe260601_1700_28016_archive.mp3" base.en "../samples/6-17"
```

**Amazon — download + transcribe:**
```bash
python download.py "https://s2.q4cdn.com/299287126/files/doc_earnings/2026/q1/generic/Amazon-Quarterly-Earnings-Report-Q1-2026-Full-Call.mp3" "../samples/6-17"
python transcribe.py "../samples/6-17/Amazon-Quarterly-Earnings-Report-Q1-2026-Full-Call.mp3" base.en "../samples/6-17"
```

**Microsoft — download + transcribe (mp4, audio extracted automatically):**
```bash
python download.py "https://mediusdl.event.microsoft.com/video-7533932/a4a066b001/VOD001.mp4?sv=2018-03-28&sr=c&sig=4p17KICnKnca%2FHX%2Bme6yP43Lq8FXVJHfxjsjOKYMo0A%3D&se=2031-04-29T23%3A11%3A42Z&sp=r" "../samples/6-17"
python transcribe.py "../samples/6-17/VOD001.mp3" base.en "../samples/6-17"
```

### Results

- All three pipelines ran successfully and produced `.txt` (human-readable) and `.json`
(structured, suitable for database storage).
- **Key limitation:** pipeline only works when you already have a direct
  download link.
---

## 2. ChatGPT Search + Web Scraper (Link Discovery)

### Motivation

The pipeline above requires a direct download URL as input. This section
documents two approaches tested to find those URLs automatically, rather
than finding them manually.

### Approach A: ChatGPT Search

Used the following prompt against Amazon, Microsoft, Apple, and HP Inc.:

```
Search [Company Name]'s official investor relations website in detail
and return a list of files related to their most recent quarterly
earnings report (audio, video, or text/document files).

For each item found, return a JSON object with these fields:
- company, ticker
- fiscal_period, quarter_end_date
- asset_type ("audio", "video", or "text")
- title, url
- is_direct_file: true if the URL points directly to a downloadable
  file (e.g. ends in .mp3, .mp4, .pdf), false if it's a webpage,
  embedded player, or portal
- hosting_platform (e.g. "ChorusCall", "Q4 Inc", "company's own domain")
- format (e.g. "mp3", "PDF", "streaming player")

Only include the company's official IR domain. Return as JSON array only.
```

Raw outputs saved to: `research/6-17/llm-search-results/`

### Approach B: Web Scraper (`src/scrape_ir_page.py`)

Scraper fetches an IR page's HTML and keyword-matches links against terms
like "webcast", "earnings call", "replay", "conference call". Outputs JSON
in the same structure as the ChatGPT results for direct comparison.

```bash
python scrape_ir_page.py "https://ir.aboutamazon.com/overview/default.aspx" "Amazon" "AMZN" "../research/6-17/scraper-results/amazon.json"
python scrape_ir_page.py "https://investors.hpe.com/news-and-events" "Hewlett Packard Enterprise" "HPE" "../research/6-17/scraper-results/hp.json"
python scrape_ir_page.py "https://investor.apple.com/investor-relations/default.aspx" "Apple Inc." "AAPL" "../research/6-17/scraper-results/apple.json"
python scrape_ir_page.py "https://www.microsoft.com/en-us/investor/earnings/fy-2026-q2/press-release-webcast" "Microsoft Corporation" "MSFT" "../research/6-17/scraper-results/microsoft.json"
```

Raw outputs saved to: `research/6-17/scraper-results/`

### Results

| Company | ChatGPT | Scraper | Direct audio found? |
|---|---|---|---|
| Amazon | Generic IR landing page only | 0 results | No |
| Apple | Generic streaming page only | 0 results | No |
| HP Inc. | Generic IR page + 1 PDF | 169 results, 2 PDFs + 1 unrelated CEO fireside chat | No |
| Microsoft | Same page URL repeated for all assets | A few results, 0 direct files | No |

### Comparison Conclusion

- Neither approach found a direct, downloadable audio file for any company.

---

## 3. Potential Idea: Quartr API + LLM API

### The Core Problem: Automating audio link discovery

### About Quartr

Quartr is a Swedish financial data company founded to aggregate and structure investor relations material from public companies globally.

**Quartr API** is their enterprise data product, relevant to the app:

- **Coverage:** 15,000+ public companies across 65 markets
- **Data available:**
  - Live and archived earnings call audio 
  - Live and historical transcripts in JSON with speaker identification and timestamps 
  - Filings and reports (10-K, 10-Q, 8-K, press releases) as PDFs
  - Slide presentations as high-resolution PDFs
  - AI-generated event summaries in Markdown
- **Technical details:**
  - REST API
  - JSON responses throughout
- **Pricing:** custom enterprise pricing

### Proposed Pipeline

The proposal is to combine Quartr API (structured IR data) with an LLM
API (Claude or ChatGPT) to produce transcript summaries for display in the app:

```
Quartr API
    → transcript JSON / audio URL per company+event
        → (if audio only) transcribe.py locally OR Quartr's own transcript
            → LLM API (Claude/ChatGPT) with transcript as context
                → structured output: summary, key metrics, sentiment
                    → the app database
                        → the app app
```

- Quartr provides the raw transcript data
- LLM layer adds the intelligence

### Open Questions / Next Steps

- Get a Quartr API pricing quote
- Think about API integration with the app backend databse
- Ask Quartr API data what companies it includes

---

## June 19-23, 2026

### Goal
For each of the 20 "Big Tech" companies on the heatmap, download the webcast audio and try to find patterns/similarities.

### Company List (20)

- Amazon (AMZN)
- Microsoft (MSFT)
- Google (GOOG)
- Meta (META)
- Tesla (TSLA)
- Taiwan Semiconductor (TSM)
- Salesforce (CRM)
- SanDisk (SNDK)
- ASML (ASML)
- Broadcom (AVGO)
- Alibaba (BABA)
- Cisco (CSCO)
- Oracle (ORCL)
- AMD (AMD)
- Qualcomm (QCOM)
- IBM (IBM)
- Texas Instruments (TXN)
- Nvidia (NVDA)
- Apple (AAPL)
- Adobe (ADBE)

### Bottom Line

- Tesla and Google hosted directly on YouTube, can download using command line. Adobe is also hosted on YouTube, but the channel isn't the company's official channel. 
```bash
pip install yt-dlp

yt-dlp -x --audio-format mp3 -o "samples/6-19/automated-test/tesla-q1-2026.%(ext)s" "https://www.youtube.com/watch?v=qO7T5zgRvXM"

yt-dlp -x --audio-format mp3 -o "samples/6-19/automated-test/google-q1-2026.%(ext)s" "https://www.youtube.com/watch?v=LPJoiDiVkTI"
```
- Apple can't be completed because the screencast/recording is only available for 2 weeks after it occurs
- Nvidia has different pipeline: `save_login_session.py` + `find_media_url.py` + `download_hls_segments.py`
  - `find_media_url.py` finds signature from URL, then `download_hls_segments.py` uses this signature to manually build each URL for each segment and then stitch the segments together into the entire file using ffmpeg concatenation
  - This is necessary because simply using the ffmpeg command drops the signature
- Pipeline built using `save_login_session.py` + 
  `find_media_url.py` is able to automate finding the correct download link (by looking through requests). This link will either be sent to download.py (if it is a mp3/mp4) or run through ffmpeg to convert to the desired format, and saved as a downloaded file (the purpose of this is to download the audio file)
- 10/20 Companies also had transcript pdfs available:
  - Google / Alphabet (GOOG)
  - Meta (META)
  - Taiwan Semiconductor (TSM)
  - Salesforce (CRM)
  - ASML (ASML)
  - Alibaba (BABA)
  - Cisco (CSCO) — prepared remarks only, not full transcript
  - AMD (AMD)
  - Qualcomm (QCOM)
  - IBM (IBM)

### `src/find_media_url.py` (Automated Link Finder)

 - Replaces the manual "open DevTools, watch network traffic, find the right URL" process with a
script. 
- Opens the page, watches everything the page loads, and
automatically picks out the real audio/video link using the two patterns we found across all the companies: either a single repeated file (handed to `download.py`) or a streaming playlist file (handed to `ffmpeg`). Full setup and run instructions are in the README.
company

### `src/download_hls_segments.py` (Construct Entire Clip for Nvidia)
- Gets signature from URL from `src/find_media_url.py`
- Uses this signature to manually build URL for each segment
- Runs `ffmpeg` to stitch together segments to construct entire recording

README includes setup/run commands and platforms tested.