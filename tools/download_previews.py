#!/usr/bin/env python3
"""Download Wikimedia candidate previews for human review, not game installation."""
import io
import json
import pathlib
import requests
import time
from PIL import Image, ImageOps
from urllib.parse import urlparse

root = pathlib.Path("output")
candidates = json.loads((root / "candidates.json").read_text(encoding="utf-8"))
preview_dir = root / "previews"
preview_dir.mkdir(parents=True, exist_ok=True)
session = requests.Session()
session.headers["User-Agent"] = "UltraAtmosphereFM27/0.1 (personal research, github.com/mirkoschubert60-byte/Ultra-Atmosphere-FM27)"
report = []
for index, item in enumerate(candidates[:20], 1):
    url = item.get("image_url", "")
    host = urlparse(url)
    entry = {"index": index, "club_id": item.get("club_id"), "title": item.get("title"),
             "source": item.get("file_page"), "artist": item.get("artist"),
             "license": item.get("license"), "license_url": item.get("license_url"),
             "status": "not_downloaded"}
    try:
        if host.scheme != "https" or host.hostname not in {"upload.wikimedia.org", "thumb.wikimedia.org"}:
            raise ValueError("Unexpected image host")
        response = None
        for attempt in range(4):
            response = session.get(url, timeout=35)
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(20, 3 * (attempt + 1)))
                continue
            break
        response.raise_for_status()
        if len(response.content) > 20_000_000:
            raise ValueError("File too large")
        image = Image.open(io.BytesIO(response.content))
        image.load()
        if image.width * image.height > 50_000_000:
            raise ValueError("Image dimensions too large")
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((800, 450))
        filename = f"candidate_{index:02d}.jpg"
        image.save(preview_dir / filename, "JPEG", quality=82)
        entry["status"] = "preview_downloaded"
        entry["preview"] = filename
    except (ValueError, requests.RequestException, OSError) as exc:
        entry["error"] = str(exc)[:300]
    report.append(entry)
    time.sleep(1.5)
(root / "preview_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("Previews downloaded:", sum(x["status"] == "preview_downloaded" for x in report), "of", len(report))
print("Note: previews are NOT approved club matches or game assets.")
