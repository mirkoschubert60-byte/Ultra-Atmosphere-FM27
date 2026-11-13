#!/usr/bin/env python3
"""Conservative source triage. Never automatically approves a picture or its license."""
import csv
import json
import pathlib
import re
import unicodedata

ROOT = pathlib.Path("output")
data = json.loads((ROOT / "candidates.json").read_text(encoding="utf-8"))

def norm(value):
    value = unicodedata.normalize("NFKD", value or "")
    return re.sub(r"[^a-z0-9 ]+", " ", "".join(c for c in value.lower() if not unicodedata.combining(c))).strip()

def assess(item):
    club = norm(item.get("club", ""))
    title = norm(item.get("title", "").replace("File:", ""))
    desc = norm(item.get("description", ""))
    source = title + " " + desc
    words = [x for x in club.split() if len(x) >= 5 and x not in {"football", "sporting", "club"}]
    match = bool(club and (club in source or (words and all(w in source for w in words))))
    positive = bool(re.search(r"\b(tifo|choreograph\w*|choreo|choreografie|choreography|choreographie)\b", source))
    opposing = ["fans of ", "supporters of ", "fan with ", "paok fc fans", "hertha berlin supporters"]
    other_team = any(t in title for t in opposing) and club not in title
    if not match or other_team:
        status, reason = "reject", "Club not clearly depicted or title identifies other supporters"
    elif positive:
        status, reason = "review_priority", "Club mentioned and tifo/choreography described"
    else:
        status, reason = "manual_review", "Club mentioned, but no confirmed choreography"
    return {"club_id": item.get("club_id"), "club": item.get("club"), "title": item.get("title"),
            "source": item.get("file_page"), "artist": item.get("artist"),
            "license": item.get("license"), "license_url": item.get("license_url"),
            "status": status, "reason": reason,
            "reviewed_club_match": False, "reviewed_license": False}

result = [assess(x) for x in data]
(ROOT / "triage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
with (ROOT / "triage.csv").open("w", newline="", encoding="utf-8") as fp:
    writer = csv.DictWriter(fp, fieldnames=list(result[0]) if result else ["club", "status"])
    writer.writeheader()
    writer.writerows(result)
for status in ("review_priority", "manual_review", "reject"):
    print(status, sum(x["status"] == status for x in result))
print("No photos or licenses automatically approved.")
