"""Questions whose answer exists only in a page image: the total on a given shop's receipt from
a given day, and the day of a given shop's receipt for a given amount. 200 scanned receipts,
indexed through OCR run here (RapidOCR); the same system over the dataset's hand
transcription is the ceiling. Measured: whether the right page comes first, whether the
answer read off it is right, and query latency at k=20."""
import json
import random
import time
from pathlib import Path

import numpy as np

from . import data
from .index import Index, Page, answer, crop, ocr_rows, parse_date

RESULTS = Path(__file__).resolve().parent.parent / "results"


def same_date(a, b):
    return a is not None and a == parse_date(b)


def same_total(a, b):
    try:
        return a is not None and abs(float(a) - float(b)) < 0.005
    except (TypeError, ValueError):
        return False


def evaluate(index, ids, gold, k=20):
    rows, times = [], []
    for i in ids:
        g = gold[i]
        for asks, q in (("total", f"total on the {g['company']} receipt dated {g['date']}"),
                        ("date", f"date of the {g['company']} receipt for {g['total']}")):
            start = time.perf_counter()
            hits = index.search(q, k, "image")
            value, row, box = answer(hits[0][0], asks)
            times.append(time.perf_counter() - start)
            ids_ranked = [p.id for p, _ in hits]
            right_page = ids_ranked[0] == f"{i:03d}"
            right = (same_total if asks == "total" else same_date)(value, g[asks])
            rows.append({"asks": asks, "top1": right_page, "top5": f"{i:03d}" in ids_ranked[:5], "answer": right_page and right,
                         "cited": box is not None})
    return rows, 1000 * float(np.percentile(times, 95))


def bench(n=200, seed=0):
    ids = sorted(random.Random(seed).sample(range(626), n))
    gold = {i: data.labels(i) for i in ids}
    ocr = {i: ocr_rows(i) for i in ids}                   # cached after the first run
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    start = time.perf_counter()
    for i in ids[:10]:                                    # time the encoder itself, uncached
        engine(str(data.image(i)))
    ocr_seconds = (time.perf_counter() - start) / 10
    systems = {"OCR run here (RapidOCR)": Index([Page(f"{i:03d}", "image", ocr[i], str(data.image(i))) for i in ids]),
               "hand transcription (ceiling)": Index([Page(f"{i:03d}", "image", data.transcription(i), str(data.image(i))) for i in ids])}
    lines = [f"{n} scanned receipts, {2 * n} questions (a total, a date). k = 20.", "",
             "| Image text from | Question | Right page first | Right page in top 5 | Right answer from it | Cited with a crop | p95 query latency |",
             "|---|---|---|---|---|---|---|"]
    summary = {}
    for name, index in systems.items():
        rows, p95 = evaluate(index, ids, gold)
        summary[name] = {"p95_ms": p95}
        for asks in ("total", "date"):
            rs = [r for r in rows if r["asks"] == asks]
            stats = {k: float(np.mean([r[k] for r in rs])) for k in ("top1", "top5", "answer", "cited")}
            summary[name][asks] = stats
            lines.append(f"| {name} | {asks} | {100 * stats['top1']:.1f}% | {100 * stats['top5']:.1f}% | {100 * stats['answer']:.1f}% | "
                         f"{100 * stats['cited']:.0f}% | {p95:.1f} ms |")
    lines += ["", f"OCR at ingestion: {ocr_seconds:.2f} s per page on this CPU (once per page, not per query)."]
    page = systems["OCR run here (RapidOCR)"].pages[0]
    value, row, box = answer(page, "total")
    crop(page, box).save(data.cache_dir() / "example_crop.png")
    lines += [f"Example: receipt {page.id}, total {value} read from the row \"{row}\" at {tuple(box)}; the crop is saved "
              f"next to the data as example_crop.png."]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "bench.md").write_text("\n".join(lines) + "\n")
    (RESULTS / "summary.json").write_text(json.dumps({"n": n, "ocr_seconds_per_page": ocr_seconds, "systems": summary}, indent=1))
    return "\n".join(lines)
