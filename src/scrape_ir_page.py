"""
scrape_ir_page.py

Given a company's investor relations (IR) page URL, scans the page's HTML
for links that look like they lead to webcasts/earnings calls, based on
keyword matching in the link text and URL.

This is a "best effort, baseline" scraper, not a robust solution: IR pages
vary company to company, and even when a relevant link is found, it often
points to a webcast *player* page (e.g. ChorusCall, Q4 Inc, Notified/ICR)
rather than a direct downloadable audio file. See findings doc for more on
this distinction.

Output is saved as JSON in the same structure as the ChatGPT LLM-search
results, so the two approaches can be compared side by side.

Usage (standalone):
    python scrape_ir_page.py <ir_page_url> <company_name> <ticker> [output_path]

    Example:
    python scrape_ir_page.py "https://investors.hpe.com/news-and-events" "Hewlett Packard Enterprise" "HPE" "../research/6-17/scraper-results/hp.json"

Usage (as a module):
    from scrape_ir_page import find_webcast_links
    links = find_webcast_links("https://investors.hpe.com/news-and-events")
"""

import sys
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Keywords that suggest a link leads to a webcast/earnings call, checked
# against both the link's visible text and its href/URL.
WEBCAST_KEYWORDS = [
    "webcast", "earnings call", "conference call", "replay",
    "listen to webcast", "audio webcast", "click here for webcast",
]

# Known third-party webcast hosting platforms, used to populate
# hosting_platform field — matching the ChatGPT output structure.
HOSTING_PLATFORMS = {
    "choruscall": "ChorusCall",
    "q4cdn": "Q4 Inc",
    "q4inc": "Q4 Inc",
    "notified": "Notified/ICR",
    "vcall": "Vcall",
    "veracast": "Veracast",
    "edgeinvestor": "Edge Media Server",
    "videonline": "VideoOnline",
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _detect_platform(url: str) -> str:
    """Detect the hosting platform from the URL, or return 'company domain'."""
    url_lower = url.lower()
    for key, name in HOSTING_PLATFORMS.items():
        if key in url_lower:
            return name
    return "company's own domain"


def _detect_format(url: str) -> str:
    """Guess the format from the URL extension."""
    url_lower = url.lower().split("?")[0]
    if url_lower.endswith(".mp3"):
        return "mp3"
    if url_lower.endswith(".mp4"):
        return "mp4"
    if url_lower.endswith(".pdf"):
        return "PDF"
    return "streaming player"


def _is_direct_file(url: str) -> bool:
    """Return True if the URL looks like a direct downloadable file."""
    url_lower = url.lower().split("?")[0]
    return any(url_lower.endswith(ext) for ext in [".mp3", ".mp4", ".wav", ".pdf", ".m4a"])


def find_webcast_links(ir_page_url: str) -> list[dict]:
    """
    Fetch the IR page and return a list of links that look webcast-related.
    Each result is a raw dict with text and url keys.
    """
    print(f"Fetching: {ir_page_url}")
    response = requests.get(ir_page_url, headers=DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    matches = []
    seen_urls = set()

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(strip=True).lower()
        href = link["href"]
        href_lower = href.lower()

        is_match = any(
            keyword in link_text or keyword in href_lower
            for keyword in WEBCAST_KEYWORDS
        )
        if is_match:
            absolute_url = urljoin(ir_page_url, href)
            if absolute_url not in seen_urls:
                seen_urls.add(absolute_url)
                matches.append({
                    "text": link.get_text(strip=True),
                    "url": absolute_url,
                })

    return matches


def format_as_json(
    matches: list[dict],
    company: str,
    ticker: str,
    ir_page_url: str,
) -> list[dict]:
    """
    Convert raw scraper matches into the same JSON structure as the
    ChatGPT LLM-search output, so both can be compared side by side.
    """
    results = []
    for match in matches:
        url = match["url"]
        results.append({
            "company": company,
            "ticker": ticker,
            "source": "scraper",
            "ir_page_scraped": ir_page_url,
            "title": match["text"],
            "url": url,
            "is_direct_file": _is_direct_file(url),
            "hosting_platform": _detect_platform(url),
            "format": _detect_format(url),
        })
    return results


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python scrape_ir_page.py <ir_page_url> <company_name> "
            "<ticker> [output_path]"
        )
        print(
            "Example: python scrape_ir_page.py "
            "\"https://investors.hpe.com/news-and-events\" "
            "\"Hewlett Packard Enterprise\" \"HPE\" "
            "\"../research/6-17/scraper-results/hp.json\""
        )
        sys.exit(1)

    ir_url = sys.argv[1]
    company = sys.argv[2]
    ticker = sys.argv[3]
    output_path = sys.argv[4] if len(sys.argv) > 4 else None

    matches = find_webcast_links(ir_url)
    formatted = format_as_json(matches, company, ticker, ir_url)

    print(f"\nFound {len(formatted)} webcast-related link(s):\n")
    print(json.dumps(formatted, indent=2))

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(formatted, indent=2), encoding="utf-8")
        print(f"\nSaved to: {output_path}")

    if formatted:
        direct = [r for r in formatted if r["is_direct_file"]]
        print(f"\n{len(direct)}/{len(formatted)} links are direct files.")
        if not direct:
            print(
                "Note: no direct downloadable files found. Links likely point "
                "to webcast player pages rather than raw audio/video files."
            )