#!/usr/bin/env python3
"""Persistent, bounded, scheduled Wikimedia research. Never auto-approves artwork."""
import argparse
import csv
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from commons_tifo import search
from triage_candidates import assess

ROOT = pathlib.Path("Data/research_batches")
ROOT.mkdir(parents=True, exist_ok=True)
STATE = ROOT / "progress.json"
RESULTS = ROOT / "candidates.jsonl"
ERRORS = ROOT / "errors.jsonl"
CATALOG = ROOT / "seed_40.json"

def append_jsonl(path, data):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--catalog", default=str(CATALOG))
    args = parser.parse_args()
    if not 1 <= args.count <= 5:
        parser.error("count must be 1..5")
    clubs = json.loads(pathlib.Path(args.catalog).read_text(encoding="utf-8"))
    if isinstance(clubs, dict):
        clubs = clubs["clubs"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"next_index": 0, "processed": 0, "errors": 0, "candidates": 0}
    start = state["next_index"]
    now = datetime.now(timezone.utc).isoformat()
    if start >= len(clubs):
        print("COMPLETE: all", len(clubs), "seed clubs processed; no further API requests")
        return
    for index in range(start, min(start + args.count, len(clubs))):
        club = clubs[index]
        found = 0
        try:
            # Search output is only a candidate. Same names can denote men's/women's clubs.
            for item in search(club["name"], limit=3):
                item["club_id"] = club["uid"]
                item["women"] = club.get("women", False)
                decision = assess(item)
                append_jsonl(RESULTS, {**item, "triage_status": decision["status"], "triage_reason": decision["reason"],
                                       "auto_approved": False, "searched_at": now})
                found += 1
            print("OK", index, club["name"], found, flush=True)
        except Exception as exc:
            append_jsonl(ERRORS, {"index": index, "uid": club["uid"], "name": club["name"],
                                  "error": str(exc), "searched_at": now, "retry_needed": True})
            state["errors"] += 1
            print("FAILED", index, club["name"], str(exc), flush=True)
        state["next_index"] = index + 1
        state["processed"] += 1
        state["candidates"] += found
        state["total_clubs"] = len(clubs)
        state["updated_at"] = now
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        time.sleep(3)
    print("PROGRESS", state["next_index"], "/", len(clubs), "candidates", state["candidates"], "errors", state["errors"], flush=True)

if __name__ == "__main__":
    main()
