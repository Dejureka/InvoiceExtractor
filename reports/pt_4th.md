# PT 4th batch — FormatSOP audit report

**Date:** 2026-09-26 (Asia/Taipei) · **Branch:** `feature/pt-4th` · **Input:** `/home/box/Downloads/PT-batch-4th/4th data/` (23 PDFs, 15 cases; no .msg files present)

**Formats:** all 23 → existing `pt_gloria_v1` (**extended**, same version 1; no new format_id). No BL / arrival notice PDFs in this batch → BL No./BL Packages/BL G.W. = N/A. All PDFs have a clean text layer (pdftotext -layout); stale-layer safeguard not triggered; OCR cross-check (Tesseract on 200-dpi renders) agrees with the text layer.

**Provenance:** 20/23 PDFs are byte-identical to `~/Downloads/_archive_FormatSOP_DONE_勿重複訓練/PTsamples_Gloria_20pdfs/` (Round4 PT mega, Auditor-passed 2026-09-10). Only **3 are new**: `40-D-26PT-404_50664923`, `90-C-26PT-405_50654372`, `90-C-26PT-405_50654373`.

## Hard-check summary

- pass 23/23 · conflict 0 · needs_gold 0
- HS missing lines: 0 / 429 (PT strict — every line has 8/10-digit HS + origin)
- Independent re-parse of every material row (next-line `CC HSCODE`) matches JSON part_no/qty/amount/origin/HS for all 429 lines; header.amount = sum(lines) = `Net invoiced value of goods` = `Value:`; G.W. = `Gross Weight:` = packing footer gross; Packages = Packing `total : N` (and = unique Shipping-unit count where Shipping units are printed).

## Per PDF

| case | file | format_id | invoice_no | date | cur | amount (=sum lines) | lines | qty | pkg | G.W. kg | incoterm | origins | HS miss | hard | soft note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 40-D-26PT-404 | `40-D-26PT-404_50664923.pdf` | `pt_gloria_v1` (existing; **new sample**) | 50664923 | 2026-08-31 | USD | 1,116.60 | 5 | 88 | 3 | 15.100 | FCA Shanghai | CN | 0 | pass | — |
| 40-D-26PT-416 | `40-D-26PT-416_50666223.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50666223 | 2026-09-08 | USD | 134.00 | 1 | 200 | 1 | 14.500 | FCA Shanghai, packaging incl | CN | 0 | pass | — |
| 50-D-26PT-408 | `50-D-26PT-408_50664997.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50664997 | 2026-08-31 | USD | 1,600.03 | 53 | 345 | 2 | 111.262 | FCA Willershausen | CN,DE,GB,MD,MY,TN,US | 0 | pass | — |
| 50-D-26PT-421 | `50-D-26PT-421_50666072.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50666072 | 2026-09-07 | USD | 681.26 | 31 | 196 | 2 | 31.177 | FCA Willershausen | CN,CZ,DE,HK,MX,SI,TW | 0 | pass | — |
| 50-D-26PT-422 | `50-D-26PT-422_50665593.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50665593 | 2026-09-03 | USD | 83.60 | 2 | 13 | 1 | 7.680 | FCA Worms | CN | 0 | pass | — |
| 50-D-26PT-423 | `50-D-26PT-423_50665862.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50665862 | 2026-09-04 | USD | 319.80 | 2 | 98 | 1 | 18.880 | FCA Worms | CN | 0 | pass | — |
| 90-C-26PT-405 | `90-C-26PT-405_50654372.pdf` | `pt_gloria_v1` (existing; **new sample**) | 50654372 | 2026-06-26 | USD | 52,165.90 | 261 | 7116 | 30 | 2,712.860 | FCA Worms | AT,CH,CN,CZ,DE,FR,HU,IN,IT,KR,MD,MX,SI,TW,US,VN | 0 | pass | — |
| 90-C-26PT-405 | `90-C-26PT-405_50654373.pdf` | `pt_gloria_v1` (existing; **new sample**) | 50654373 | 2026-06-26 | USD | 1,456.00 | 1 | 800 | 1 | 65.000 | FCA Worms | CN | 0 | pass | — |
| 90-S-26PT-407 | `90-S-26PT-407_50663797.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50663797 | 2026-08-24 | USD | 4,509.80 | 10 | 2740 | 5 | 239.400 | FCA Hangzhou | CN | 0 | pass | — |
| 90-S-26PT-407 | `90-S-26PT-407_50663901.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50663901 | 2026-08-24 | USD | 20,053.84 | 4 | 208 | 4 | 895.920 | FCA Hangzhou | CN | 0 | pass | — |
| 90-S-26PT-409 | `90-S-26PT-409_50663231.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50663231 | 2026-08-19 | USD | 14,918.40 | 4 | 20160 | 12 | 4,100.000 | FCA Shanghai | CN | 0 | pass | soft: packing rows sum 1 != total_pkg 12 (Packing details summary kept; verify on PDF) |
| 90-S-26PT-410 | `90-S-26PT-410_50662910.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50662910 | 2026-08-17 | USD | 14,980.86 | 5 | 430 | 5 | 1,280.304 | FCA CHENGDU | CN | 0 | pass | — |
| 90-S-26PT-411 | `90-S-26PT-411_50664363.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50664363 | 2026-08-27 | USD | 21,879.36 | 10 | 720 | 10 | 1,906.000 | FCA CHENGDU | CN | 0 | pass | — |
| 90-S-26PT-412 | `90-S-26PT-412_50663621.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50663621 | 2026-08-21 | USD | 5,221.44 | 2 | 144 | 2 | 356.576 | FCA CHENGDU | CN | 0 | pass | — |
| 90-S-26PT-413 | `90-S-26PT-413_50664949.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50664949 | 2026-08-31 | USD | 592.00 | 4 | 500 | 2 | 46.800 | FCA Hangzhou | CN | 0 | pass | — |
| 90-S-26PT-414 | `90-S-26PT-414_50665615.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50665615 | 2026-09-03 | USD | 7,150.08 | 8 | 96 | 8 | 1,721.600 | FCA Jingshen | CN | 0 | pass | — |
| 90-S-26PT-415 | `90-S-26PT-415_50664640.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50664640 | 2026-08-28 | USD | 3,881.76 | 1 | 48 | 1 | 132.016 | FCA Dongguan | CN | 0 | pass | — |
| 90-S-26PT-417 | `90-S-26PT-417_50664925.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50664925 | 2026-08-31 | USD | 2,169.60 | 6 | 480 | 6 | 71.640 | FCA Tianjin | CN | 0 | pass | — |
| 90-S-26PT-418 | `90-S-26PT-418_50664217.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50664217 | 2026-08-26 | USD | 41,674.97 | 11 | 957 | 11 | 1,664.900 | FCA Penang | MY | 0 | pass | soft: mixed HS digit lengths [8, 10] (as printed: 84672920) |
| 90-S-26PT-418 | `90-S-26PT-418_50664379.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50664379 | 2026-08-27 | USD | 19,981.44 | 2 | 144 | 2 | 233.700 | FCA Penang | MY | 0 | pass | — |
| 90-S-26PT-419 | `90-S-26PT-419_50665577.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50665577 | 2026-09-03 | USD | 2,154.00 | 1 | 200 | 1 | 48.000 | FCA Hangzhou | CN | 0 | pass | — |
| 90-S-26PT-419 | `90-S-26PT-419_50665578.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50665578 | 2026-09-03 | USD | 730.80 | 4 | 340 | 3 | 32.300 | FCA Hangzhou | CN | 0 | pass | — |
| 90-S-26PT-419 | `90-S-26PT-419_50665811.pdf` | `pt_gloria_v1` (existing, identical R4 sample) | 50665811 | 2026-09-04 | USD | 2,575.68 | 1 | 48 | 1 | 82.336 | FCA Hangzhou | CN | 0 | pass | — |

## pt_gloria_v1 extension (PT 4th)

- Packing-type vocabulary for the no-Shipping-unit fallback: `Bosch-Standard-Palette (HT) …`, `Palette`, `Slip sheet 1200* 800` (seen in 50654372/50654373/50665811); `Carton X02` already covered.
- No-Shipping-unit fallback now prefers the Packing-details grand `total : N` over a partial type sum (Shipping-unit count still wins when present — unchanged).
- Soft (non-blocking) `meta.notes`: packing-row sum ≠ total_pkg (50663231: one row qty 1 vs `total : 12`), Shipping-unit count ≠ Packing total, mixed HS digit lengths (50664217: `84672920` among `8467290000`).
- No extracted value changed on any of the 23 PDFs or the 14 PT round3 PDFs (diffed vs main); only the two soft notes were added.

## Items for human / manual verification

| file | reason | tool value |
|---|---|---|
| `90-S-26PT-409_50663231.pdf` | Vendor inconsistency: Packing-details row lists **1** × P.13 Folding Box with Euro Pallet (3,679.2 / 4,100 kg) but summary says `P.13 Folding Box with Euro Pallet : 12` / `total : 12` | total_pkg = **12** (summary kept; soft note) |
| `90-S-26PT-418_50664217.pdf` | Mixed HS precision: `0.601.9E0.0C1` (2 lines) printed as 8-digit `84672920`, others 10-digit `8467290000` (tariff block lists both) | kept as printed |
| `90-S-26PT-414_50665615.pdf` | Incoterm place printed `FCA Jingshen` (possible vendor typo; other Chinese shipments use Hangzhou/Shanghai/Chengdu/Dongguan/Tianjin) | kept as printed `FCA Jingshen` |
| `90-S-26PT-414_50665615.pdf` | Page-1 `Departure country` blank (not an extracted field; line origins CN present) | — |

No needs_gold, no conflicts, no scanned PDFs.

## Review pack

`docs/review_shots/pt_4th/<stem>-keyfields.png` (extracted key-field panel + PDF crops: header Invoice No./Date/Departure country, first line rows with Origin/Tarif Code, Net invoiced value/Total/Incoterm, Gross Weight/Value, Packing details summary+total) and `<stem>.json` for all 23 PDFs.

## Tests

`tests/test_pt_4th.py` + fixtures `fixtures/pt4_*_layout.txt(.gz)` (50664923, 50654372, 50654373, 50663231, 50664217, 50665811).

Hard pass ≠ final accept — Auditor verdict pending.
