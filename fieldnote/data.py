"""Scanned receipts (SROIE, ICDAR 2019): the page image, the dataset's hand transcription of it
(text and boxes), and the labelled company, date and total. Downloaded on first use, from a
pinned commit of the repository that redistributes it, into FIELDNOTE_DATA (default
~/.cache/fieldnote)."""
import json
import os
import time
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/zzzDavid/ICDAR-2019-SROIE/27be4271b251c256f695acbade9a801bffe85994/data"


def cache_dir():
    path = Path(os.environ.get("FIELDNOTE_DATA", Path.home() / ".cache" / "fieldnote"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch(rel, tries=4):
    target = cache_dir() / rel
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(tries):
            try:
                with urllib.request.urlopen(f"{BASE}/{rel}", timeout=60) as r:
                    target.write_bytes(r.read())
                break
            except OSError:
                if attempt == tries - 1:
                    raise
                time.sleep(2 ** attempt)
    return target


def rows(boxes):
    """Boxes on the same printed line, joined left to right: [(text, (x0, y0, x1, y1))]."""
    if not boxes:
        return []
    height = sorted(b[3] - b[1] for _, b in boxes)[len(boxes) // 2] or 1
    out = []
    for text, b in sorted(boxes, key=lambda tb: ((tb[1][1] + tb[1][3]) / 2, tb[1][0])):
        c = (b[1] + b[3]) / 2
        if out and abs(c - out[-1][2]) <= height / 2:
            segs, box, cc = out[-1]
            out[-1] = (segs + [(b[0], text)], (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])), cc)
        else:
            out.append(([(b[0], text)], b, c))
    return [(" ".join(t for _, t in sorted(s)), box) for s, box, _ in out]


def transcription(i):
    boxes = []
    for raw in fetch(f"box/{i:03d}.csv").read_text(encoding="utf-8", errors="replace").splitlines():
        p = raw.split(",", 8)
        if len(p) == 9 and p[8].strip():
            xs, ys = [int(v) for v in p[0:8:2]], [int(v) for v in p[1:8:2]]
            boxes.append((p[8].strip(), (min(xs), min(ys), max(xs), max(ys))))
    return rows(boxes)


def labels(i):
    return json.loads(fetch(f"key/{i:03d}.json").read_text(encoding="utf-8"))


def image(i):
    return fetch(f"img/{i:03d}.jpg")
