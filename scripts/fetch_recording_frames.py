#!/usr/bin/env python3
"""Grab lecture-recording frames at given timestamps and crop them by layout.

Usage:
    python3 fetch_recording_frames.py LIST.tsv OUT_DIR --url-template TEMPLATE [--contact-sheet]

LIST.tsv rows (tab separated):  name  entry_id  h:mm:ss  layout
layout is one of:
  full       the whole frame is the shared screen      -> fetch 1920 wide, resize to 1280
  composite  presenter camera left, screen right       -> fetch 1920 wide, keep right half
  camera     lecture-hall camera only (projector)      -> fetch 2560 wide, crop right screen
TEMPLATE is the platform's frame/thumbnail URL with {entry}, {width} and {sec}
placeholders (for Kaltura: copy a thumbnail URL from the channel page and add
.../width/{width}/vid_sec/{sec}). Failed requests are retried 1-3 s later.
Requires Pillow for cropping and contact sheets.
"""
import argparse
import os
import sys
import time
import urllib.request

WIDTH = {"full": 1920, "composite": 1920, "camera": 2560}


def seconds(ts):
    parts = [int(p) for p in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            raise IOError("HTTP %s" % resp.status)
        data = resp.read()
    with open(dest, "wb") as fh:
        fh.write(data)


def crop(path, layout, out):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if layout == "full":
        im = im.resize((1280, round(h * 1280 / w)))
    elif layout == "composite":
        im = im.crop((w // 2, round(h * 0.25), w, round(h * 0.75)))
    elif layout == "camera":
        im = im.crop((round(w * 0.51), round(h * 0.20), round(w * 0.995), round(h * 0.70)))
    im.save(out, quality=85)


def contact_sheet(names, out_dir, cols=3, w=640):
    from PIL import Image, ImageDraw
    tiles = [Image.open(os.path.join(out_dir, n + ".jpg")) for n in names]
    h = max(round(t.height * w / t.width) for t in tiles)
    sheet_paths = []
    per = cols * 3
    for k in range(0, len(tiles), per):
        chunk = list(zip(names[k:k + per], tiles[k:k + per]))
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w, rows * (h + 22)), "white")
        d = ImageDraw.Draw(sheet)
        for i, (n, t) in enumerate(chunk):
            x, y = (i % cols) * w, (i // cols) * (h + 22)
            sheet.paste(t.resize((w, round(t.height * w / t.width))), (x, y + 22))
            d.text((x + 4, y + 4), n, fill="black")
        p = os.path.join(out_dir, "_contact_%02d.jpg" % (k // per))
        sheet.save(p, quality=80)
        sheet_paths.append(p)
    return sheet_paths


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("list")
    ap.add_argument("out_dir")
    ap.add_argument("--url-template", required=True)
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--keep-raw", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    done, failed = [], []
    for line in open(args.list, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, entry, ts, layout = line.split("\t")[:4]
        raw = os.path.join(args.out_dir, "raw_" + name + ".jpg")
        ok = False
        for delta in (0, 1, 2, 3):
            url = args.url_template.format(entry=entry, width=WIDTH.get(layout, 1920),
                                           sec=seconds(ts) + delta)
            try:
                fetch(url, raw)
                ok = True
                break
            except Exception:
                time.sleep(1)
        if not ok:
            failed.append(name)
            continue
        crop(raw, layout, os.path.join(args.out_dir, name + ".jpg"))
        if not args.keep_raw:
            os.remove(raw)
        done.append(name)
    print("frames: %d ok, %d failed %s" % (len(done), len(failed), failed or ""))
    if args.contact_sheet and done:
        for p in contact_sheet(done, args.out_dir):
            print("contact sheet:", p)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
