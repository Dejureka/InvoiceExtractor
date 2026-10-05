# BHC 4th + 5th — Auditor Round 2 (2026-10-05)

Fixes for Auditor reviews of `feature/bhc-4th` @ 80642b2 (4th) and @ 05212ee (5th).
Rule: a value printed clearly on the BL face must not stay needs_gold / wrong.

## Root causes

| BL | format | page OCR (before) | why |
|---|---|---|---|
| 4th case1 `20260921141756-0001.pdf` | `tvl_hbl_v1` | r1 200 dpi `SHAKEL26871822` / `3488,000KGS`; r2 300 dpi BL no OK, **no GW** | thin 200-dpi bilevel scan; full-page `--psm 6` swaps single glyphs (1→4, 5→8). Only one GW read → kept as suggestion. |
| 5th case1 `20260929142515-0001.pdf` | `tvl_hbl_v1` | `18 PALLETS ! 1 1498.500KGS` (r2 row 1495.5) | same failure mode (1→4/8, 6→18). No separate 1498.5 printed. |
| 4th case6 `BL.pdf` | `jif_cosmo_waybill_v1` | `SHE, 998, 000` (thousands group lost), no pallet line | anti-counterfeit background = 1–2 px horizontal hatch; module ran ONE OCR pass, so GW could never reach ≥2 reads. |
| 4th case8 `WAYBILL.pdf` | `jif_cosmo_waybill_v1` | `3,084,500` ×1, `CONTAINER<10 PALLETS` ×1 | same: one pass → one read each → needs_gold although correct. |

## Fix (no case values hard-coded)

- New `src/invoice_extractor/ocr_reread.py` (pymupdf + tesseract only):
  `page_words` (OCR pass with word boxes; optional `remove_hlines` = vertical opening that drops thin hatch lines and keeps glyph strokes) and
  `reread_clip` (OCR only the located value as one line, `--psm 7` + whitelist, at several zooms; each zoom = one read in the existing vote).
- `tvl_hbl_v1`: locate the face weight token (`…KGS`) and B/L no (`SHAKEL…`/`QDEX…`) on a 200-dpi pass, re-read at 200/300/400 dpi.
  GW re-reads only when the face has exactly **one** weight token (multi-container faces keep the row-sum vote).
  Token consensus (≥2 agreeing, strict majority) also overrules a disagreeing slash-row page read. B/L no with a clear majority incl. re-reads → no needs_gold.
  `SHAKEL 26971822` (space) now parsed.
- `jif_cosmo_waybill_v1`: second page pass at 300 dpi with the hatch removed (adds pkg reads `N PALLETS (… PIECES)` / `CONTAINER<N PALLETS` and the SAID-TO-CONTAIN GW) + weight re-read at 300/400/600 dpi.
  Vote threshold unchanged (≥2 agreeing reads, strict majority). `0 PALLETS` (from `C0 PALLETS`) ignored.
- Cost: +2–3 s per scanned TVL / JIFFA BL.

## New key fields

| batch / case | BL No. | BL pkg | BL GW | needs_gold | reads (from meta.notes) |
|---|---|---|---|---|---|
| 4th case1 | SHAKEL26971822 | 8 | **3185** (was 3488) | none (was bl_no, bl_gw) | GW face_r1=3488, tok200/300/400=3185; BL no r1=…268…, r2 + tok×3=…269… |
| 4th case6 | 260918KEE103 | 16 | **1998** (was blank) | none (was bl_pkg, bl_gw) | pkg attached-sheet 16, clean pallets(pieces) 16, clean container<16; GW clean 1998, tok300/400/600=1998 |
| 4th case8 | 260918KEE102 | 10 | 3084.5 | none (was bl_pkg, bl_gw) | pkg r1 container<10, clean ×2 =10; GW r1 3084.5, clean 3084.5, tok×3 3084.5 |
| 5th case1 | SHAKEL26971867 | 6 | **1195.5** (was 1498.5) | none (was bl_gw) | GW face_r1=1498.5, rows_r2=1495.5, tok200/300/400=1195.5 |

Case 8 INV side unchanged: shared PL `shipment_first` — 117 (PDF + xlsx) 10 / 3084.5, 121 (PDF + xlsx) 0 / 0 + Summary note; **user confirmed 2026-10-05** as the BHC rule (SOP updated).
Case 8 scan copy `20260921195744-0001.pdf` (same BL no) still unreadable → still collapsed / not used.

## Regression

- Re-ran all BHC 4th cases 1–11 and BHC 5th cases 1–3 end-to-end vs the review packs: only the BL fields / flags above changed; every INV header + line list identical.
- Old scanned TVL BLs (BHC 2nd case1 jpg / case7 / case8, BHC 3rd case4 / case7), old code vs new: identical except BHC 2nd case7 `SHAKEL26970898` 1 / 231 — values unchanged (= earlier audited gold), the GW needs_gold flag is now cleared (face token re-read 231 ×3).
- pytest: **295 passed, 3 skipped** (new `tests/test_bhc_rereads.py`: 9 fixture tests + 4 real-scan tests that skip when the scans / tesseract are absent).
