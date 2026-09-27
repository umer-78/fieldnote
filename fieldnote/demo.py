"""python -m fieldnote.demo   write the live demo's data (docs/data.json): results/summary.json and, for the first
12 receipts of the bench, which page each question retrieved and the box its answer was read from. No receipt
text is committed: the page loads the images and labels from the dataset's public copy when it opens."""
import json
import random
from pathlib import Path

from . import data
from .bench import same_date, same_total
from .index import Index, Page, answer, ocr_rows

ROOT = Path(__file__).resolve().parent.parent


def build(out=ROOT / "docs", n=200, show=12, seed=0):
    summary = json.loads((ROOT / "results" / "summary.json").read_text())
    ids = sorted(random.Random(seed).sample(range(626), n))            # the bench's receipts, in the bench's order
    index = Index([Page(f"{i:03d}", "image", ocr_rows(i), str(data.image(i))) for i in ids])
    examples = []
    for i in ids[:show]:
        g = data.labels(i)
        for asks, q in (("total", f"total on the {g['company']} receipt dated {g['date']}"),
                        ("date", f"date of the {g['company']} receipt for {g['total']}")):
            hits = index.search(q, 20, "image")
            value, _, box = answer(hits[0][0], asks)
            ranked = [p.id for p, _ in hits]
            examples.append({"receipt": f"{i:03d}", "asks": asks, "top": ranked[:5], "right_page": ranked[0] == f"{i:03d}",
                             "right_answer": ranked[0] == f"{i:03d}" and (same_total if asks == "total" else same_date)(value, g[asks]),
                             "box": [int(x) for x in box] if box is not None else None})
    out.mkdir(exist_ok=True)
    (out / "data.json").write_text(json.dumps({"summary": summary, "base": data.BASE, "examples": examples}, indent=1))
    print(f"wrote {out / 'data.json'}: {len(examples)} questions")


if __name__ == "__main__":
    build()
