200 scanned receipts, 400 questions (a total, a date). k = 20.

| Image text from | Question | Right page first | Right page in top 5 | Right answer from it | Cited with a crop | p95 query latency |
|---|---|---|---|---|---|---|
| OCR run here (RapidOCR) | total | 87.5% | 99.0% | 63.5% | 100% | 2.3 ms |
| OCR run here (RapidOCR) | date | 70.5% | 89.0% | 58.0% | 98% | 2.3 ms |
| hand transcription (ceiling) | total | 91.5% | 99.5% | 69.0% | 100% | 2.3 ms |
| hand transcription (ceiling) | date | 74.0% | 90.5% | 72.0% | 100% | 2.3 ms |

OCR at ingestion: 1.71 s per page on this CPU (once per page, not per query).
Example: receipt 001, total 60.31 read from the row "TOTALAMT. RM 60.31" at (27, 690, 375, 713); the crop is saved next to the data as example_crop.png.
