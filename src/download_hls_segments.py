"""
download_hls_segments.py

Workaround for HLS streams where the signed Policy/Signature query string
covers the whole event (via a wildcard Resource pattern) but ffmpeg
doesn't propagate that query string when following the manifest's
internal segment references -- causing 403 errors on every segment even
though the signature is actually valid for all of them.

This script downloads each numbered segment directly (manually appending
the known-good Policy/Signature to each one), then concatenates them all
into a single output file using ffmpeg's concat demuxer.

Confirmed working case: Nvidia's Veracast-hosted webcast, where the
master manifest -> child manifest -> individual .ts segments all 403'd
through ffmpeg's normal HLS handling, but each segment downloads fine
when given the same signed query string directly.

Usage:
    python download_hls_segments.py <base_url_pattern> <query_string> <num_segments> <output_path> [start_num] [num_digits]

    Example (Nvidia, 175 segments, 5-digit zero-padded numbering):
    python download_hls_segments.py \\
        "https://bofa.veracast.com/vod/webcasts/bofa/globaltech2026/events/3031_keynot/3031_keynot_a8_a8" \\
        "Policy=eyJ...&Signature=klu...&Key-Pair-Id=K3U..." \\
        175 \\
        "../samples/6-19/automated-test/nvidia-full.mp4"
"""

import sys
import subprocess
from pathlib import Path

import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def download_segments(
    base_url_pattern: str,
    query_string: str,
    num_segments: int,
    output_path: str,
    start_num: int = 1,
    num_digits: int = 5,
    temp_dir: str = "hls_segments_temp",
) -> Path:
    """
    Download numbered segments like {base_url_pattern}_00001.ts?{query_string},
    {base_url_pattern}_00002.ts?{query_string}, etc., then concatenate
    them all into one file at output_path using ffmpeg.
    """
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    segment_files = []
    failed_segments = []

    for i in range(start_num, start_num + num_segments):
        segment_num = str(i).zfill(num_digits)
        url = f"{base_url_pattern}_{segment_num}.ts?{query_string}"
        local_path = temp_dir / f"segment_{segment_num}.ts"

        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
            response.raise_for_status()
            local_path.write_bytes(response.content)
            segment_files.append(local_path)
            print(f"  [{i}/{start_num + num_segments - 1}] Downloaded segment {segment_num}")
        except requests.exceptions.RequestException as e:
            print(f"  [{i}/{start_num + num_segments - 1}] FAILED segment {segment_num}: {e}")
            failed_segments.append(segment_num)

    if failed_segments:
        print(f"\nWarning: {len(failed_segments)} segment(s) failed to download: {failed_segments}")
        print("The final video may have gaps where these segments are missing.")

    if not segment_files:
        raise RuntimeError("No segments downloaded successfully -- cannot create output file.")

    # Build an ffmpeg concat list file
    concat_list_path = temp_dir / "concat_list.txt"
    with open(concat_list_path, "w") as f:
        for seg in segment_files:
            f.write(f"file '{seg.resolve()}'\n")

    print(f"\nConcatenating {len(segment_files)} segments into {output_path}...")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list_path),
            "-c", "copy",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concatenation failed:\n{result.stderr}")

    print(f"Done. Output saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "Usage: python download_hls_segments.py <base_url_pattern> "
            "<query_string> <num_segments> <output_path> [start_num] [num_digits]"
        )
        sys.exit(1)

    base_url_pattern = sys.argv[1]
    query_string = sys.argv[2]
    num_segments = int(sys.argv[3])
    output_path = sys.argv[4]
    start_num = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    num_digits = int(sys.argv[6]) if len(sys.argv) > 6 else 5

    download_segments(
        base_url_pattern, query_string, num_segments, output_path,
        start_num=start_num, num_digits=num_digits,
    )