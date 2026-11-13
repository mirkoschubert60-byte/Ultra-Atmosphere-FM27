#!/usr/bin/env python3
"""Free Wikimedia Commons tifo researcher and PNG exporter.

Usage:
 python tools/commons_tifo.py --club "Eintracht Frankfurt" --club-id 911
 python tools/commons_tifo.py --catalog clubs_catalog.json --limit 10

Outputs are candidates, not verified in-game assets. Review every club match.
"""
import argparse
import csv
import html
import io
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "UltraAtmosphereFM27/0.1 (noncommercial research; GitHub repository mirkoschubert60-byte/Ultra-Atmosphere-FM27)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
ALLOWED_HOSTS = {"upload.wikimedia.org", "thumb.wikimedia.org"}
OUT = Path("output")


def query(params):
    params = {"format": "json", "formatversion": 2, **params}
    for attempt in range(3):
        try:
            response = SESSION.get(API, params=params, timeout=35)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def search(club, limit=8):
    # Searches are only candidates: never assert a photograph depicts this club.
    terms = [f'"{club}" tifo', f'"{club}" choreography', f'"{club}" fans']
    seen = set()
    for term in terms:
        data = query({"action": "query", "generator": "search", "gsrsearch": term,
                      "gsrnamespace": 6, "gsrlimit": limit,
                      "prop": "imageinfo", "iiprop": "url|extmetadata|mime",
                      "iiurlwidth": 1600})
        for page in data.get("query", {}).get("pages", []):
            title = page.get("title", "")
            if title in seen:
                continue
            seen.add(title)
            info = (page.get("imageinfo") or [{}])[0]
            metadata = info.get("extmetadata", {})
            def meta(k):
                return html.unescape(re.sub(r"<[^>]*>", "", metadata.get(k, {}).get("value", ""))).strip()
            url = info.get("thumburl") or info.get("url", "")
            yield {"club": club, "title": title, "file_page": info.get("descriptionurl", ""),
                   "image_url": url, "mime": info.get("mime", ""),
                   "artist": meta("Artist"), "license": meta("LicenseShortName"),
                   "license_url": meta("LicenseUrl"), "attribution": meta("Attribution"),
                   "description": meta("ImageDescription"),
                   "reviewed_club_match": False, "reviewed_license": False}
        time.sleep(0.6)


def download(candidate, destination):
    url = candidate["image_url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Image host not permitted")
    response = SESSION.get(url, timeout=60, stream=True)
    response.raise_for_status()
    content = bytearray()
    for chunk in response.iter_content(1024 * 64):
        content.extend(chunk)
        if len(content) > 30 * 1024 * 1024:
            raise ValueError("Image exceeds 30 MB")
    image = Image.open(io.BytesIO(content))
    image.load()
    if image.width * image.height > 75_000_000:
        raise ValueError("Image dimensions exceed safety limit")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.fit(image, (1600, 900), method=Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--club")
    parser.add_argument("--club-id")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--download-reviewed", action="store_true",
                        help="Only download explicitly approved candidates from output/reviewed.json")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.download_reviewed:
        reviewed = json.loads((OUT / "reviewed.json").read_text(encoding="utf-8"))
        for item in reviewed:
            if not (item.get("reviewed_club_match") and item.get("reviewed_license")):
                continue
            if not item.get("license") or not item.get("artist"):
                continue
            download(item, OUT / "png" / f'{int(item["club_id"])}.png')
            print("Exported", item["club_id"])
        return
    clubs = []
    if args.club:
        clubs.append({"uid": args.club_id, "name": args.club})
    if args.catalog:
        payload = json.loads(args.catalog.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("clubs", [])
        clubs.extend(payload[:max(0, args.limit)])
    if not clubs:
        parser.error("Provide --club or --catalog")
    candidates = []
    for club in clubs:
        name = club.get("name", "")
        uid = club.get("uid", club.get("id"))
        if not name:
            continue
        try:
            for item in search(name):
                item["club_id"] = uid
                candidates.append(item)
            print(name, "candidates:", sum(x["club_id"] == uid for x in candidates))
        except (requests.RequestException, ValueError) as exc:
            print("Search error", name, str(exc))
    (OUT / "candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    with (OUT / "candidates.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["club_id", "club", "title", "file_page", "artist", "license", "license_url",
                  "reviewed_club_match", "reviewed_license"]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)
    print("Candidates saved:", len(candidates), "- NOT approved or downloaded.")


if __name__ == "__main__":
    main()
