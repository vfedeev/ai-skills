#!/usr/bin/env python3
"""
Compact transcript parser — reads Groq verbose_json and outputs clean [MM:SS] text.

Usage:
    python3 compact_transcript.py /tmp/transcript.json --from 48:00 --to 80:00
    python3 compact_transcript.py /tmp/transcript.json --offset 2880

Output: one line per segment, format [MM:SS] text
"""

import json
import sys
import argparse


def parse_time(t: str) -> float:
    """Parse MM:SS or HH:MM:SS to seconds."""
    parts = t.strip().split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0


def format_ts(secs: float) -> str:
    """Seconds to [MM:SS]."""
    s = int(secs)
    return f"[{s // 60:02d}:{s % 60:02d}]"


def main():
    parser = argparse.ArgumentParser(description="Compact transcript from Groq JSON")
    parser.add_argument("input", help="JSON file path or - for stdin")
    parser.add_argument("--from", dest="time_from", default=None, help="Start time (MM:SS)")
    parser.add_argument("--to", dest="time_to", default=None, help="End time (MM:SS)")
    parser.add_argument("--offset", type=float, default=0, help="Add offset in seconds to timestamps")
    args = parser.parse_args()

    # Read input
    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.input) as f:
            data = json.load(f)

    segments = data.get("segments", [])
    if not segments and "text" in data:
        print(data["text"])
        return

    # Filter by time range
    t_from = parse_time(args.time_from) if args.time_from else 0
    t_to = parse_time(args.time_to) if args.time_to else float("inf")

    for seg in segments:
        start = seg.get("start", 0) + args.offset
        if start < t_from or start > t_to:
            continue
        text = seg.get("text", "").strip()
        if text:
            print(f"{format_ts(start)} {text}")


if __name__ == "__main__":
    main()
