#!/usr/bin/env python3
"""Find exam-related statements in timestamped transcript TSVs and print them with context.

Usage:
    python3 find_exam_mentions.py [--tier A,B,C] [--context 3] [--extra REGEX] TSV [TSV ...]

Input rows come from transcript_segments.py (index, h:mm:ss, sentence).
Tiers:
  A  direct exam words (quiz, exam, midterm, MCQ, negative marking, calculator, venue ...)
  B  emphasis / exclusion (not tested, remember this, most important, memorize ...)
  C  in-class quiz markers (wooclap, QR code, next question, closing in ...)
Matches use word boundaries so that "exam" does not hit "example". Always read
the printed context before treating a hit as exam information: lecturers often
use quiz scores or exams as analogies.
"""
import argparse
import re
import sys

TIERS = {
    "A": r"\bquiz(?:zes)?\b|\bexam(?:s|ination|inable)?\b|\bmid[- ]?terms?\b|\bfinals?\b|\bmcqs?\b|"
         r"multiple[- ](?:choice|answers?)|single answer|short answer|true or false|fill in the blanks?|"
         r"open[- ]book|clos(?:e|ed)[- ]book|calculators?|cheat ?sheet|lock ?down|respondus|"
         r"negative mark(?:s|ing)?|partial (?:mark|credit)|floor(?:ed)? to(?:wards?)? zero|"
         r"make ?up|compulsory|weightage|percent(?:age)?|\bseat(?:ing)?\b|\bvenue\b|hardware lab|software lab|\blab\b|"
         r"sample (?:quiz|questions?)|past[- ]year|till (?:the end of )?week|up to week|until week",
    "B": r"not (?:be |going to be )?tested|not going to test|won'?t (?:be )?test|will (?:not )?ask you|"
         r"test you|be tested|come out|remember (?:this|that|the)|please remember|just remember|take note|"
         r"most important|very important|really important|memori[sz]e|need to know|must know|"
         r"all you need to know|trick(?:y| question)|common mistake|golden rule|focus on",
    "C": r"woo ?clap|wool ?clap|wood ?clap|\bqr code\b|event code|next question|closing in|votes? (?:are )?closed|"
         r"mini quiz|correct answer",
}


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3:
                rows.append((parts[1], parts[2]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--tier", default="A,B,C")
    ap.add_argument("--context", type=int, default=3, help="sentences of context before/after")
    ap.add_argument("--extra", default="", help="additional regex (course-specific terms)")
    ap.add_argument("--summary", action="store_true", help="only print hit counts per file")
    args = ap.parse_args()
    pats = [TIERS[t.strip().upper()] for t in args.tier.split(",") if t.strip()]
    if args.extra:
        pats.append(args.extra)
    rx = re.compile("|".join("(?:%s)" % p for p in pats), re.I)
    for path in args.files:
        rows = load(path)
        hits = [i for i, (_, s) in enumerate(rows) if rx.search(s)]
        print("=== %s  (%d hits)" % (path, len(hits)))
        if args.summary:
            continue
        shown = set()
        for i in hits:
            if i in shown:
                continue
            lo, hi = max(0, i - args.context), min(len(rows), i + args.context + 1)
            print("--- hit at %s" % rows[i][0])
            for j in range(lo, hi):
                mark = ">>" if rx.search(rows[j][1]) else "  "
                print("%s %s  %s" % (mark, rows[j][0], rows[j][1]))
                if rx.search(rows[j][1]):
                    shown.add(j)
    return 0


if __name__ == "__main__":
    sys.exit(main())
