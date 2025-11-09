#!/usr/bin/env python3
"""
Script to fetch a markdown file from a GitHub-hosted folder and run yt-dlp
for a time segment found on the first line that contains a link and a time range.

Usage:
    python vhs.py 3213
"""

import re
import sys
import subprocess
from typing import Optional, Tuple
from urllib import request, error

PREFIX = "https://raw.githubusercontent.com/snegovik2049/screenshot/refs/heads/main/data/posts"
# ==================================


def thousand_bucket(n: int) -> int:
    if n % 1000 == 0:
        return n
    return (n // 1000 + 1) * 1000


def fetch_md(url: str) -> str:
    req = request.Request(url, headers={"User-Agent": "curl/7.0 (python-urllib)"})
    try:
        with request.urlopen(req, timeout=20) as resp:
            charset = resp.headers.get_content_charset() or 'utf-8'
            return resp.read().decode(charset, errors='replace')
    except error.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code} when fetching {url}: {e.reason}")
    except error.URLError as e:
        raise RuntimeError(f"Failed to fetch {url}: {e.reason}")


TIME_PART = r"\d{1,2}"
TIME_RE = r"(?:{p}(?::{p}){{0,2}})".format(p=TIME_PART) 

URL_AND_TIMERANGE = re.compile(
    r"(?P<url>https?://[^\s)]+).*?(?P<start>" + TIME_RE + r")\s*-\s*(?P<end>" + TIME_RE + r")",
    re.IGNORECASE,
)



def normalize_time(t: str) -> str:
    parts = t.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 1:
        h, m, s = 0, 0, parts[0]
    elif len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    elif len(parts) == 3:
        h, m, s = parts
    else:
        raise ValueError(f"Unsupported time format: {t}")
    m += s // 60
    s = s % 60
    h += m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def clean_url(s: str) -> str:
    import html, re
    s = s.encode('utf-8').decode('unicode-escape', errors='ignore')
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", "", s) 
    s = s.replace("</a>", "").strip()
    s = s.rstrip('.,);\"\'')
    return s



def find_first_url_and_timerange(md: str):
    for line in md.splitlines():
        m = URL_AND_TIMERANGE.search(line)
        if m:
            url = clean_url(m.group('url'))
            return url, m.group('start'), m.group('end')
    return None, None, None


def build_yt_dlp_cmd(n: int, url: str, start: str, end: str) -> list:
    start_n = normalize_time(start)
    end_n = normalize_time(end)
    section = f"*{start_n}-{end_n}"
    out_template = f"{n}.mp4"
    cmd = [
        "yt-dlp",
        "-f", "mp4",
        "-o", out_template,
        url,
        "--download-sections", section,
    ]
    return cmd


def main():
    if len(sys.argv) != 2:
        print("Usage: python yt_dlp_from_github.py <number>")
        sys.exit(2)

    try:
        n = int(sys.argv[1])
    except ValueError:
        print("<number> must be an integer")
        sys.exit(2)

    bucket = thousand_bucket(n)
    url = f"{PREFIX}/{bucket}/{n}.md"
    print(f"Fetching markdown from: {url}")

    try:
        md = fetch_md(url)
    except Exception as e:
        print(f"Error fetching markdown: {e}")
        sys.exit(1)

    found = find_first_url_and_timerange(md)
    if not found:
        print("No URL + time-range pattern found in the markdown file.")
        sys.exit(1)

    video_url, start, end = found
    print(f"Found URL: {video_url}")
    print(f"Found time range: {start} - {end}")

    cmd = build_yt_dlp_cmd(n, video_url, start, end)
    print("Running command:")
    print(' '.join(f'"{c}"' if ' ' in c else c for c in cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"yt-dlp failed with exit code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == '__main__':
    main()
