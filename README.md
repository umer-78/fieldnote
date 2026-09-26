# fieldnote

Retrieval-augmented answers whose evidence exists only inside a picture. Each modality is indexed by its own encoder, and every answer comes back with the page it came from and a crop of the region that holds it, so a person can check the number by eye.

Converting an image to a caption throws away the values a question needs: "a photo of a receipt from a bakery" doesn't contain the total. So page images here are indexed through their text as read off the image, with each row's position kept. The encoder is RapidOCR, a real OCR model run locally. Answers are read from those rows, and the cited crop comes from the original image.

**Scope, honestly.** The spec's corpus is HVAC manuals with charts, job-site photos and support-call recordings. None of that is public, and this environment can't reach image-embedding models (CLIP, SigLIP), speech models (Whisper) or a vision LLM. What is here:

- **Image pages.** Scanned receipts (SROIE, 626 real scans) are the pages whose numbers exist only in the image. They go through a real OCR encoder, run here.
- **Text pages.** Text documents share the same index, tagged by modality, with fusion across modalities by reciprocal rank.
- **Audio.** An audio modality fits the same interface through any transcriber, but none is bundled.
- **Not run.** There is no caption-only baseline (no captioning model is available) and no vision-LLM synthesis.

## Results

`python -m fieldnote bench`: 200 scanned receipts and 400 questions. Half ask for a total ("the total on the {shop} receipt dated {date}"); half ask for a date ("the date of the {shop} receipt for {amount}"). k = 20. The same system over the dataset's hand transcription of each scan is the ceiling: what perfect OCR would give.

| Image text from | Question | Right page first | Right page in top 5 | Right answer from it | Cited with a crop | p95 query latency |
|---|---|---|---|---|---|---|
| OCR run here (RapidOCR) | total | 87.5% | 99.0% | 63.5% | 100% | 2.3 ms |
| OCR run here (RapidOCR) | date | 70.5% | 89.0% | 58.0% | 98% | 2.3 ms |
| hand transcription (ceiling) | total | 91.5% | 99.5% | 69.0% | 100% | 2.3 ms |
| hand transcription (ceiling) | date | 74.0% | 90.5% | 72.0% | 100% | 2.3 ms |

- **Retrieval from images works through OCR.** The right receipt is first for 87.5% of total questions and in the top 5 for 99%, within 4 points of perfect transcription. OCR that drops spaces ("BOOKTA_K(TAMANDAYA)SDNBHD") is handled by matching on character n-grams over letters and digits only.
- **Reading the answer is the weak step:** 63.5% of totals and 58% of dates are right end to end.
  - Even perfect transcription only gets 69% and 72% with these reading rules.
  - Real OCR costs another 5–14 points, most on dates, where a misread digit changes the value.
  - A vision-language model reading the cited crop is the natural next step. The crop is already returned for it.
- **Every answer carries its source.** Each has the receipt id, the row it was read from and that row's box, cropped from the scan (for example, receipt 001: total 60.31 from "TOTALAMT. RM 60.31").
- **Latency.** The p95 query latency is under 3 ms at k = 20; OCR runs once per page at ingestion, 1.7 s per page on this CPU. The spec's gate was p95 under 6 seconds.

## How it works

```python
from fieldnote.index import Index, Page, answer, crop, ocr_rows
from fieldnote import data

pages = [Page(f"{i:03d}", "image", ocr_rows(i), str(data.image(i))) for i in range(50)]
pages.append(Page("manual-7", "text", [("Unit 7 trips on high pressure when ...", (0, 0, 0, 0))], "manual.md"))
index = Index(pages)
hits = index.search("total on the gardenia bakeries receipt dated 12/01/2018", k=20, modality="image")
value, row, box = answer(hits[0][0], "total")
crop(hits[0][0], box).save("evidence.png")          # the cited crop
index.fused("high pressure trip")                   # reciprocal rank fusion across modalities
```

- `fieldnote/index.py`: the modality-tagged pages, the OCR encoder (RapidOCR, cached per page), character n-gram retrieval with a modality filter, fusion, answer reading and crops.
- `fieldnote/data.py`: the SROIE scans and their hand transcription, from a pinned commit.

```bash
pip install -e '.[dev]'
pytest -q
python -m fieldnote bench     # first run OCRs 200 scans (a few minutes), then seconds
```

The scans are downloaded on first use into `~/.cache/fieldnote`; nothing is committed.
