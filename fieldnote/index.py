"""A modality-tagged index. Each modality has its own encoder into rows of text with locations:
images through OCR (RapidOCR, run here on every page image, keeping each row's box), text
documents by paragraph, audio through any transcriber (none bundled here). Retrieval runs per
modality and fuses the ranked lists (reciprocal rank fusion); the answer comes back with the
page it came from and the crop of the row that holds it."""
import json
import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from . import data

AMOUNT = re.compile(r"(\d{1,5}[.,]\d{2})(?!\d)")
DATE = re.compile(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})")


def squash(text):
    """OCR drops and inserts spaces; compare on letters and digits only."""
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


@dataclass
class Page:
    id: str
    modality: str             # image, text or audio
    rows: list                # [(text, box)]
    source: str               # where the page lives (an image path, a document path)


def ocr_rows(i, engine=None):
    """RapidOCR over a page image, cached: rows with their boxes."""
    path = data.cache_dir() / "ocr" / f"{i:03d}.json"
    if not path.exists():
        from rapidocr_onnxruntime import RapidOCR
        engine = engine or RapidOCR()
        result, _ = engine(str(data.image(i)))
        boxes = [(t, (min(p[0] for p in b), min(p[1] for p in b), max(p[0] for p in b), max(p[1] for p in b)))
                 for b, t, _ in (result or [])]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([(t, [int(v) for v in box]) for t, box in data.rows(boxes)]))
    return [(t, tuple(b)) for t, b in json.loads(path.read_text())]


class Index:
    def __init__(self, pages):
        self.pages = pages
        self.vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), sublinear_tf=True)
        self.x = self.vec.fit_transform([squash(" ".join(t for t, _ in p.rows)) for p in pages])

    def search(self, query, k=20, modality=None):
        scores = (self.x @ self.vec.transform([squash(query)]).T).toarray().ravel()
        order = [i for i in np.argsort(-scores) if modality is None or self.pages[i].modality == modality]
        return [(self.pages[i], float(scores[i])) for i in order[:k]]

    def fused(self, query, k=20, modalities=("image", "text", "audio"), c=60):
        """Reciprocal rank fusion of the per-modality rankings."""
        score = {}
        for m in modalities:
            for rank, (p, _) in enumerate(self.search(query, k, m)):
                score[p.id] = score.get(p.id, 0) + 1 / (c + rank + 1)
        by_id = {p.id: p for p in self.pages}
        return [by_id[i] for i in sorted(score, key=lambda i: -score[i])[:k]]


MONTHS = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
DATES = re.compile(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})|(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})|"
                   r"(\d{1,2})\s*[-/ ]?\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s*[-/ ]?\s*(\d{2,4})", re.I)
NOT_THE_TOTAL = re.compile(r"SUB|QTY|QUANTITY|DISC|CASH|CHANGE|TENDER|SAVING|ITEM", re.I)


def parse_date(text):
    """The first real date in the text as YYYY-MM-DD (day-first, year-first or month names), or None."""
    from datetime import date
    for m in DATES.finditer(text or ""):
        g = m.groups()
        try:
            d, mo, y = (int(g[0]), int(g[1]), int(g[2])) if g[0] else (int(g[5]), int(g[4]), int(g[3])) if g[3] else \
                (int(g[6]), MONTHS[g[7][:3].upper()], int(g[8]))
            return date(y + (2000 if y < 100 else 0), mo, d).isoformat()
        except (ValueError, KeyError):
            continue
    return None


def answer(page, asks):
    """(value, the row it came from, its box) for 'total' or 'date', read off the page's rows.
    The total is the largest amount on a TOTAL row that is not a quantity, discount or change."""
    rows = page.rows
    if asks == "total":
        cands = [(float(a.replace(",", ".")), t, b) for t, b in rows if "TOTAL" in squash(t) and not NOT_THE_TOTAL.search(t)
                 for a in AMOUNT.findall(t)]
        if not cands:
            cands = [(float(a.replace(",", ".")), t, b) for t, b in rows if not NOT_THE_TOTAL.search(t) for a in AMOUNT.findall(t)]
        best = max(cands, default=None)
        return (f"{best[0]:.2f}", best[1], best[2]) if best else (None, None, None)
    for text, box in rows:
        d = parse_date(text)
        if d:
            return d, text, box
    return None, None, None


def crop(page, box, pad=6):
    """The cropped region of the page image that holds the answer, so it can be checked by eye."""
    from PIL import Image
    img = Image.open(page.source)
    x0, y0, x1, y1 = box
    return img.crop((max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad))
