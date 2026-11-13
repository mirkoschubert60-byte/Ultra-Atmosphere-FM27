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
STATE = ROOT / "world_progress.json"
RESULTS = ROOT / "world_candidates.jsonl"
ERRORS = ROOT / "world_errors.jsonl"
CATALOG = ROOT / "seed_40.json"

def append_jsonl(path, data):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--catalog", default=str(CATALOG))
    args = parser.parse_args()
    if not 1 <= args.count <= 50:
        parser.error("count must be 1..50")
    catalog_path = pathlib.Path(args.catalog)
    if catalog_path.is_dir():
        parts = sorted(catalog_path.glob("part_*.json"))
        if len(parts) != 43:
            raise RuntimeError(f"Expected 43 catalog parts; found {len(parts)}. Refusing incomplete scan.")
        clubs = []
        for part in parts:
            clubs.extend(json.loads(part.read_text(encoding="utf-8")))
        if len(clubs) != 42757:
            raise RuntimeError(f"Expected 42757 clubs; got {len(clubs)}")
        global STATE, RESULTS, ERRORS
        STATE = ROOT / "world_progress.json"
        RESULTS = ROOT / "world_candidates.jsonl"
        ERRORS = ROOT / "world_errors.jsonl"
    else:
        clubs = json.loads(catalog_path.read_text(encoding="utf-8"))
    if isinstance(clubs, dict):
        clubs = clubs["clubs"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"next_index": 0, "processed": 0, "errors": 0, "candidates": 0}
    catalog_id = "world-42757-v1" if catalog_path.is_dir() else "seed-40-v1"
    if state.get("catalog_id") != catalog_id:
        state = {"next_index": 0, "processed": 0, "errors": 0, "candidates": 0, "catalog_id": catalog_id}
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
