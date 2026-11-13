#!/usr/bin/env python3
"""Small, rate-limited, resumable FM27 club photo research batches."""
import argparse
import csv
import json
import pathlib
import time
from commons_tifo import search
from triage_candidates import assess

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="Data/research_batches/seed_40.json")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--count", type=int, default=5)
    args = ap.parse_args()
    if args.offset < 0 or not 1 <= args.count <= 10:
        ap.error("offset must be nonnegative; count 1..10")
    clubs = json.loads(pathlib.Path(args.catalog).read_text(encoding="utf-8"))
    if isinstance(clubs, dict):
        clubs = clubs["clubs"]
    selected = clubs[args.offset:args.offset + args.count]
    out = pathlib.Path("output")
    out.mkdir(exist_ok=True)
    rows = []
    for club in selected:
        name = club["name"]
        uid = club["uid"]
        try:
            # Two Commons searches per club, max 3 per query; no forced approval.
            for item in search(name, limit=3):
                item["club_id"] = uid
                item["women"] = club.get("women", False)
                decision = assess(item)
                rows.append({**item, "triage_status": decision["status"],
                             "triage_reason": decision["reason"]})
            print("Club", uid, name, "candidates", sum(r["club_id"] == uid for r in rows), flush=True)
        except Exception as exc:
            print("ERROR", uid, name, str(exc), flush=True)
        time.sleep(2)
    (out / "batch_candidates.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out / "batch_summary.csv").open("w", newline="", encoding="utf-8") as f:
        columns = ["club_id","club","women","title","file_page","artist","license","license_url","triage_status","triage_reason"]
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print("Total candidate records", len(rows), "for", len(selected), "clubs", flush=True)
    print("Images remain unverified; no assets automatically distributed.", flush=True)

if __name__ == "__main__":
    main()
