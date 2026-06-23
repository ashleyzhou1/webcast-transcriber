# webcast-transcriber

A Python pipeline for downloading, transcribing, and extracting text from company earnings call webcasts and press releases.

---

## Project Structure

```
the app-webcast-transcriber/
├── src/                          # Python scripts
│   ├── download.py
│   ├── transcribe.py
│   ├── extract_pdf.py
│   ├── scrape_ir_page.py
│   ├── translate.py
│   ├── find_media_url.py
│   ├── save_login_session.py
│   ├── download_hls_segments.py
│   └── test_all_companies.sh
├── research/                     # Findings log and research outputs
│   ├── findings.md
│   ├── 6-17/
│   │   ├── llm-search-results/
│   │   └── scraper-results/
│   └── 6-19/
├── samples/                      # Outputs (audio/video not included in repo)
│   ├── 6-17/
│   └── 6-19/
│       └── automated-test/
├── requirements.txt
└── README.md
```

---

## Setup

Requires Python 3.10+, pip, and ffmpeg.

```bash
git clone git@github.com:ashleyzhou1/the app-webcast-transcriber.git
cd the app-webcast-transcriber
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

**`src/translate.py`** — translate a transcript or extracted text file into another language using the Google Translate API.
```bash
python translate.py <text_file> <target_lang_code> [output_dir]
# Example: python translate.py ../samples/6-17/amazon-q1-2026.txt zh ../samples/6-17
```

**`src/scrape_ir_page.py`** — scrape a company IR page for webcast-related links and save results as JSON.
```bash
python scrape_ir_page.py <ir_page_url> <company_name> <ticker> [output_path]
```

> **Note:** scripts default to writing output to `../samples`. Pass an output directory explicitly if running from a different location.

---

## Finding & Downloading Webcast Audio/Video

### find_media_url.py

Given a webcast page URL, automatically finds the downloadable
audio/video link by watching the page's network traffic (replaces
manual browser DevTools inspection). It looks for one of three patterns,
in priority order:

1. **A direct media file** (same file requested multiple times with
   "206 Partial Content" status) → hands off to `download.py`
2. **Numbered HLS segments with a signed URL** (e.g. `..._00001.ts`,
   `..._00002.ts`) → hands off to `download_hls_segments.py` (see Nvidia
   section below for why this is needed instead of just using ffmpeg
   directly on the manifest)
3. **A streaming playlist file** (`.m3u8`) with no numbered segments
   found → hands off to `ffmpeg`, which fetches and reassembles the full
   stream directly

```bash
python find_media_url.py <webcast_page_url> [session_file.json] [--debug]
```

`--debug` is required to allow the user to manually click play.

### Step 1: Save a login session (one-time per platform)

Login once per platform. This login info is saved to a JSON file. Log in
manually, then press Enter.

```bash
python src/save_login_session.py "<a login page URL on that platform>" "<platform>_session.json"
```

**Platforms encountered so far, and which companies use them:**

| Platform | Companies | Session file name |
|---|---|---|
| Q4 Inc (`events.q4inc.com`) | Oracle, Meta, Cisco | `q4inc_session.json` |
| ChorusCall (`event.choruscall.com`) | Qualcomm, IBM | `choruscall_session.json` |
| edge.media-server.com | SanDisk, Broadcom, AMD, TI, Alibaba | `media_server_session.json` |
| Veracast (`bofa.veracast.com`) | Nvidia (see special handling below) | `veracast_session.json` |

`find_media_url.py` auto-picks the right session file based on the
platform in the URL you give it (see `PLATFORM_SESSIONS` near the top of
the script — add an entry there for any new platform you encounter).

**Important:** If `find_media_url.py` opens to a login screen instead of
the webcast, log in again manually in that window (just means the saved
session timed out on the browser's end).

### Batch testing multiple companies (test_all_companies.sh)

To run the link-finding process across many companies in one sitting,
edit the `COMPANIES` list near the top of `src/test_all_companies.sh`:

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

The script automatically downloads/converts each result to mp3 and saves
it to the output folder set at the top of the script.

**Nvidia is intentionally NOT included in this script.** Its platform
(Veracast) needs an extra manual step the others don't — confirming the
total segment count before downloading (see below) — so it can't run
unattended in a loop the same way the rest can. It's a one-time manual
process instead.

### YouTube-hosted webcasts (e.g. Tesla, Google/Alphabet)

For YouTube-hosted webcasts, use `yt-dlp`:
```bash
pip install yt-dlp
```
```bash
yt-dlp -x --audio-format mp3 -o "<output_dir>/<company>.%(ext)s" "<youtube_watch_url>"
```

Example (Tesla):
```bash
yt-dlp -x --audio-format mp3 -o "samples/6-19/automated-test/tesla-q1-2026.%(ext)s" "https://www.youtube.com/watch?v=qO7T5zgRvXM"
```

---

## Nvidia (Special Case): Signed HLS Segments

Nvidia's webcast platform (Veracast) breaks the video into many small,
numbered chunks (e.g. `..._00001.ts` through `..._00175.ts`), each
requiring a signed permission token (`?Policy=...&Signature=...`) to
download.

**The problem:** ffmpeg can read the `.m3u8` manifest fine when given the signed link directly, but it does NOT carry that signature forward when it goes to fetch the individual chunks listed inside the manifest.

**Solution:** the signature is valid across all chunks of that event (not locked to one specific chunk), so `download_hls_segments.py` downloads each chunk directly with that same signature manually re-attached, then stitches them all together into one file with ffmpeg.

**This is a one-time, mostly-manual process:**

1. Run `find_media_url.py` on Nvidia's page. It will detect the numbered-segment pattern and print a ready-to-fill `download_hls_segments.py` command, missing only the segment count.
2. Find the total segment count using `curl` to fetch the manifest's raw ext:

```bash
curl -s "<m3u8_url_with_query_string>" | tail -5
```

   This prints the last few lines of the manifest, which include the final segment's filename (e.g. `..._00175.ts` means 175 total segments).

3. Fill in that count and run the printed command:

```bash
python src/download_hls_segments.py \
  "<base_url_from_find_media_url_output>" \
  "<query_string_from_find_media_url_output>" \
  <num_segments> \
  "<output_path>.mp4" \
  1 <num_digits>
```

Example (confirmed working, 175 segments):
```bash
python src/download_hls_segments.py \
  "https://bofa.veracast.com/vod/webcasts/bofa/globaltech2026/events/3031_keynot/3031_keynot_a8_a8" \
  "Policy=...&Signature=...&Key-Pair-Id=..." \
  175 \
  "samples/6-19/automated-test/nvidia-full.mp4" \
  1 5
```

This same workaround would apply to any future platform with the same
"signature doesn't propagate through ffmpeg's manifest chain" problem —
`find_media_url.py` will auto-detect that pattern going forward.

---

## Sample Files

Audio and video files are not included in this repo. [Click here for Google Drive for test files.](https://drive.google.com/drive/folders/17D9ajhhCqGy4qU3mu6fG-iW5j5QBlE0b?usp=share_link)

Transcript outputs (`.txt`, `.json`, and PDFs where available) are included directly in `samples/6-17/` and `samples/6-19/`.

