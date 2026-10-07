#!/usr/bin/env python3
"""Split lecture transcripts into timestamped sentences (one TSV per input).

Usage:
    python3 transcript_segments.py OUT_DIR FILE [FILE ...]

Accepted inputs:
  * Kaltura "Attachments" word timelines (.json): a list of objects with
    w (word), s (start ms), e (end ms);
  * WebVTT caption files (.vtt).

Each output row is: index <TAB> h:mm:ss <TAB> sentence. Sentences end at
., ? or ! (after at least three words) or at a pause longer than --gap ms.
"""
import argparse
import json
import os
import re
import sys


def fmt(ms):
    s = int(ms) // 1000
    return "%d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60)


def words_from_json(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("words") or data.get("items") or []
    for w in data:
        if isinstance(w, dict) and "w" in w and "s" in w:
            yield w["w"], int(w["s"]), int(w.get("e", w["s"]))


def cues_from_vtt(path):
    ts = re.compile(r"(\d+):(\d\d):(\d\d)[.,](\d{3})\s*-->\s*(\d+):(\d\d):(\d\d)[.,](\d{3})")
    ts2 = re.compile(r"(\d\d):(\d\d)[.,](\d{3})\s*-->\s*(\d\d):(\d\d)[.,](\d{3})")
    start = end = None
    buf = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            m = ts.search(line)
            m2 = None if m else ts2.search(line)
            if m or m2:
                if buf and start is not None:
                    yield " ".join(buf), start, end
                buf = []
                if m:
                    g = list(map(int, m.groups()))
                    start = ((g[0] * 60 + g[1]) * 60 + g[2]) * 1000 + g[3]
                    end = ((g[4] * 60 + g[5]) * 60 + g[6]) * 1000 + g[7]
                else:
                    g = list(map(int, m2.groups()))
                    start = (g[0] * 60 + g[1]) * 1000 + g[2]
                    end = (g[3] * 60 + g[4]) * 1000 + g[5]
            elif line and start is not None and not line.isdigit() and line != "WEBVTT":
                buf.append(re.sub(r"<[^>]+>", "", line))
    if buf and start is not None:
        yield " ".join(buf), start, end


def sentences(tokens, gap):
    cur, st, last = [], None, 0
    for text, s, e in tokens:
        if cur and s - last > gap:
            yield st, " ".join(cur)
            cur, st = [], None
        if st is None:
            st = s
        cur.append(text)
        last = e
        if re.search(r"[.?!]$", text) and len(cur) >= 3:
            yield st, " ".join(cur)
            cur, st = [], None
    if cur:
        yield st, " ".join(cur)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out_dir")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--gap", type=int, default=1500, help="pause (ms) that ends a sentence")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    written = set()
    for path in args.files:
        if path.lower().endswith(".json"):
            toks = words_from_json(path)
        elif path.lower().endswith(".vtt"):
            toks = cues_from_vtt(path)
        else:
            print("skip (unsupported): %s" % path, file=sys.stderr)
            continue
        base, ext = os.path.splitext(os.path.basename(path))
        if base in written:
            base = base + ext.replace(".", "_")
        written.add(base)
        out = os.path.join(args.out_dir, base + ".tsv")
        n = 0
        with open(out, "w", encoding="utf-8") as fh:
            for i, (st, text) in enumerate(sentences(toks, args.gap)):
                fh.write("%d\t%s\t%s\n" % (i, fmt(st or 0), text.replace("\t", " ")))
                n += 1
        print("%s\t%d sentences" % (out, n))


if __name__ == "__main__":
    main()
