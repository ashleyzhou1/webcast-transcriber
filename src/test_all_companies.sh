#!/bin/bash
#
# test_all_companies.sh
#
# Loops through a list of company webcast page URLs, runs find_media_url.py
# on each (which requires YOU to manually click play when prompted), then
# automatically downloads/converts the result to mp3 using either
# download.py (for direct files) or ffmpeg (for .m3u8 streams).
#
# Output goes to samples/6-19/automated-test/<company>.mp3
#
# Usage (run from project root):
#   bash src/test_all_companies.sh
#
# Note: This does not run transcribe.py. It stops once the mp3 is
# downloaded, so you can manually verify each file before transcribing.

OUTPUT_DIR="samples/6-19/automated-test"
mkdir -p "$OUTPUT_DIR"

# Format: "company_name|webcast_page_url"
# Excludes Tesla, Nvidia, Apple, Adobe, Google per today's scope.
COMPANIES=(
  "alibaba|https://edge.media-server.com/mmc/p/npqai6e2/"
  "asml|https://www.asml.com/en/investors/financial-results/q1-2026"
)

echo "=================================================="
echo "Testing ${#COMPANIES[@]} companies"
echo "Output folder: $OUTPUT_DIR"
echo "=================================================="
echo ""
echo "For each company, a browser window will open."
echo "Click Play, then come back to this terminal and press Enter."
echo ""

for entry in "${COMPANIES[@]}"; do
  IFS='|' read -r company url <<< "$entry"

  echo ""
  echo "=================================================="
  echo "Company: $company"
  echo "URL: $url"
  echo "=================================================="

  RESULT=$(python src/find_media_url.py "$url" --debug 2>&1) || {
    echo "  find_media_url.py failed for $company, skipping."
    echo "$RESULT" >> "$OUTPUT_DIR/${company}_error.log"
    continue
  }

  echo "$RESULT"

  DIRECT_LINE=$(echo "$RESULT" | grep 'python download.py' || true)
  M3U8_LINE=$(echo "$RESULT" | grep 'ffmpeg -i' || true)

  OUTPUT_FILE="$OUTPUT_DIR/${company}.mp3"
    if [[ -n "$DIRECT_LINE" ]]; then
        # Extract the URL between the first pair of quotes
        MEDIA_URL=$(echo "$DIRECT_LINE" | sed -E 's/.*download\.py "([^"]+)".*/\1/')
        echo "  Downloading direct file for $company ..."
        DOWNLOAD_OK=false
        for attempt in 1 2 3; do
        if python src/download.py "$MEDIA_URL" "$OUTPUT_DIR"; then
            DOWNLOAD_OK=true
            break
        else
            echo "  Attempt $attempt failed, retrying in 3s..."
            sleep 3
        fi
        done
        if [[ "$DOWNLOAD_OK" == "true" ]]; then
        echo "  NOTE: check $OUTPUT_DIR for the downloaded file and rename to ${company}.mp3 if needed"
        else
        echo "  All 3 download attempts failed for $company. Skipping."
        echo "$MEDIA_URL" >> "$OUTPUT_DIR/${company}_download_failed.log"
        fi

  elif [[ -n "$M3U8_LINE" ]]; then
    MEDIA_URL=$(echo "$M3U8_LINE" | sed -E 's/.*-i "([^"]+)".*/\1/')
    echo "  Converting HLS stream for $company via ffmpeg ..."
    if ffmpeg -y -i "$MEDIA_URL" "$OUTPUT_FILE" -loglevel error; then
      echo "  Saved: $OUTPUT_FILE"
    else
      echo "  ffmpeg failed for $company. Skipping."
      echo "$MEDIA_URL" >> "$OUTPUT_DIR/${company}_ffmpeg_failed.log"
    fi
  

  else
    echo "  No media URL found for $company. Logging as failed."
    echo "$RESULT" >> "$OUTPUT_DIR/${company}_no_match.log"
  fi
done

echo ""
echo "=================================================="
echo "Done. Check $OUTPUT_DIR for results."
echo "Any companies that failed have a .log file explaining why."
echo "=================================================="