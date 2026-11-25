# Regression vs main (`11818d8`)

Baseline saved from current main, then re-run on `fix/bhc-my-hub-9028-invoice-no`.

| Batch | Invoices | Hard | Warn | Diffs | OCR skips | Failures |
| --- | --- | --- | --- | --- | --- | --- |
| ma3 | 184 | 0 | 14 | 0 | 20 | 0 |
| pt4 | 23 | 0 | 0 | 0 | 0 | 0 |
| bhc4 | 14 | 0 | 108 | 0 | 11 | 0 |
| bhc5 | 2 | 0 | 1 | 0 | 5 | 0 |
| bhc6 | 19 | 0 | 126 | 0 | 11 | 0 |
| ebike1 | 18 | 0 | 22 | 0 | 0 | 0 |
| soe2 | 10 | 0 | 0 | 0 | 5 | 0 |
| maak | 3 | 0 | 0 | 0 | 0 | 0 |

**Diff vs main = 0.** No baseline value changes, no Auditor snapshot differences, no extraction failures. OCR skips are the same as the main baseline (scans; this box has no tesseract).

Full report (including the OCR-skip list): `out/regress/report-my-hub-9028.md`.
