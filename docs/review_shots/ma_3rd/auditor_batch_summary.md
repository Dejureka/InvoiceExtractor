# MA 3rd (last MA batch): FormatSOP audit pack

> **Round 2 (2026-09-29):** see `round2/round2_summary.md`. BL formats now output only the Result columns (BL No. / BL Packages / BL G.W.); vessel / voyage / ETA / ETD / CBM etc. in the tables below are Round 1 and no longer extracted. 008/036 shared RB: deduped shipment pkg/GW on the first invoice, others 0 (008: 2120394532 = 26 / 1989.836; 036: 2120422517 = 32 / 2801.031). Excel/JSON in this folder are the Round 2 output.

**Date:** 2026-09-29 (Asia/Taipei)  
**Root:** `/home/box/Downloads/MA-batch-final/MA_3rd data/3rd data/`: **39 folders** (RBDEsea 19 + RBJPsea 20), 223 PDFs = 184 INV + 39 BL  
**Branch:** `feature/ma-3rd` (not merged to main)  
**Missing BL:** none. Every folder has exactly one BL/arrival document.  
**Summary policy:** each INV row carries the folder's shared `BL No.` / `BL Packages` / `BL G.W. (kgs)`. Invoice Packages / G.W. are never overwritten.

## Formats

| side | format_id | status | notes |
|------|-----------|--------|-------|
| INV (RBDEsea `90-C-26MA-*`, `INVOICE 2120xxxxxx.PDF`) | `ma_with_period_v1` | existing, **unchanged** | 35 INV. HS 8-digit = printed `HS CODE`. RB pkg/GW from the INV packing section. |
| INV (RBJPsea `90-KWE-26MA-*`, `00…_2000…_RBTW_….PDF`) | `ma_no_period_v1` | existing, **unchanged** | 149 INV. HS 10-digit. |
| BL (RBDEsea `BL##########.PDF`) | `cosco_arrival_v1` | **new family** | COSCO SHIPPING 到貨通知 / ARRIVAL NOTICE, text layer. `B/L Number: COSU…`; pkg/GW from the attachment `Total:` row, cross-checked against the page-1 container row (a mismatch gives needs_gold); ETA from `ETA AT POD … ON:`; vessel/voyage/POD/container/seal/FCL/invoice refs. |
| BL (RBJPsea `robert bosch.pdf` etc.) | `kwe_sea_waybill_v1` | **new family** | KINTETSU WORLD EXPRESS / APL LOGISTICS SEA WAYBILL (scans, page 2 = KWE 請求書 / attached sheet). Read by OCR. Waybill `1220########` (majority vote); pkg/GW need ≥2 agreeing reads and a strict majority, otherwise needs_gold. ETD = LADEN ON BOARD; **no ETA on this document**. |

Other rule changes (no old semantics changed):
- `looks_like_bl_filename` accepts `BL##########`.
- `text_layer_looks_mojibake`: a scanner's CJK-mode OCR layer over an English page is treated as unreliable, so the file is OCR'd instead (backend `ocr/tesseract+prefer_over_stale_layer`). Across all 424 sample PDFs in Downloads, only the 6 JP waybills below trigger it.
- A BL needs_gold now propagates to the INV row (`needs_gold_fields += bl_*`).
- A shared BL is extracted once per folder (cache).

## Per-folder results (hard verdict: 184/184 INV pass, 39/39 BL pass)

| folder | INVs | INV format | BL file | BL format / backend | BL No. | BL pkg / GW | INV sum pkg / GW | Δ (INV−BL) | hard |
|---|---|---|---|---|---|---|---|---|---|
| 90-C-26MA-007 | 2 | ma_with_period_v1 | BL6437826540.PDF | cosco_arrival_v1 / text | COSU6437826540 | 33 / 2457.362 | 33 / 2457.364 | GW +0.002 (rounding) | pass ×2 |
| 90-C-26MA-008 | 2 | ma_with_period_v1 | BL6431163410.PDF | cosco_arrival_v1 / text | COSU6431163410 | 26 / 1989.837 | 27 / 2001.44 | **pkg +1 / GW +11.603** | pass ×2 |
| 90-C-26MA-036 | 3 | ma_with_period_v1 | BL6438665680.PDF | cosco_arrival_v1 / text | COSU6438665680 | 32 / 2801.033 | 33 / 2884.531 | **pkg +1 / GW +83.498** | pass ×3 |
| 90-C-26MA-037 | 2 | ma_with_period_v1 | BL6439218260.PDF | cosco_arrival_v1 / text | COSU6439218260 | 28 / 2236.896 | 28 / 2236.9 | GW +0.004 (rounding) | pass ×2 |
| 90-C-26MA-038 | 2 | ma_with_period_v1 | BL6439771710.PDF | cosco_arrival_v1 / text | COSU6439771710 | 29 / 3156.353 | 29 / 3156.354 | GW +0.001 (rounding) | pass ×2 |
| 90-C-26MA-039 | 2 | ma_with_period_v1 | BL6439386770.PDF | cosco_arrival_v1 / text | COSU6439386770 | 29 / 1599.82 | 29 / 1599.819 | GW -0.001 (rounding) | pass ×2 |
| 90-C-26MA-040 | 2 | ma_with_period_v1 | BL6440883030.PDF | cosco_arrival_v1 / text | COSU6440883030 | 26 / 2403.434 | 26 / 2403.427 | GW -0.007 (rounding) | pass ×2 |
| 90-C-26MA-130 | 1 | ma_with_period_v1 | BL6441817950.PDF | cosco_arrival_v1 / text | COSU6441817950 | 28 / 7019.08 | 28 / 7019.074 | GW -0.006 (rounding) | pass ×1 |
| 90-C-26MA-131 | 2 | ma_with_period_v1 | BL6442832660.PDF | cosco_arrival_v1 / text | COSU6442832660 | 34 / 2646.965 | 34 / 2646.966 | GW +0.001 (rounding) | pass ×2 |
| 90-C-26MA-132 | 2 | ma_with_period_v1 | BL6443500350.PDF | cosco_arrival_v1 / text | COSU6443500350 | 36 / 2236.755 | 36 / 2236.752 | GW -0.003 (rounding) | pass ×2 |
| 90-C-26MA-190 | 1 | ma_with_period_v1 | BL6445127890.PDF | cosco_arrival_v1 / text | COSU6445127890 | 34 / 2652.171 | 34 / 2652.171 | exact | pass ×1 |
| 90-C-26MA-191 | 1 | ma_with_period_v1 | BL6445485580.PDF | cosco_arrival_v1 / text | COSU6445485580 | 28 / 3369.028 | 28 / 3369.027 | GW -0.001 (rounding) | pass ×1 |
| 90-C-26MA-192 | 2 | ma_with_period_v1 | BL6446621010.PDF | cosco_arrival_v1 / text | COSU6446621010 | 42 / 3846.432 | 42 / 3846.436 | GW +0.004 (rounding) | pass ×2 |
| 90-C-26MA-193 | 1 | ma_with_period_v1 | BL6447129640.PDF | cosco_arrival_v1 / text | COSU6447129640 | 59 / 4383.13 | 59 / 4383.124 | GW -0.006 (rounding) | pass ×1 |
| 90-C-26MA-260 | 2 | ma_with_period_v1 | BL6447417770.PDF | cosco_arrival_v1 / text | COSU6447417770 | 22 / 18410 | 22 / 18410 | exact | pass ×2 |
| 90-C-26MA-261 | 2 | ma_with_period_v1 | BL6447418930.PDF | cosco_arrival_v1 / text | COSU6447418930 | 10 / 8763 | 10 / 8763 | exact | pass ×2 |
| 90-C-26MA-262 | 2 | ma_with_period_v1 | BL6447427150.PDF | cosco_arrival_v1 / text | COSU6447427150 | 24 / 20264 | 24 / 20264 | exact | pass ×2 |
| 90-C-26MA-263 | 2 | ma_with_period_v1 | BL6448344810.PDF | cosco_arrival_v1 / text | COSU6448344810 | 37 / 2909.47 | 37 / 2909.483 | GW +0.013 (rounding) | pass ×2 |
| 90-C-26MA-264 | 2 | ma_with_period_v1 | BL6449088340.PDF | cosco_arrival_v1 / text | COSU6449088340 | 24 / 21119 | 24 / 21119 | exact | pass ×2 |
| 90-KWE-26MA-012 | 11 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040099094 | 15 / 2962 | 15 / 2962 | exact | pass ×11 |
| 90-KWE-26MA-041 | 5 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040099422 | 5 / 431 | 5 / 431 | exact | pass ×5 |
| 90-KWE-26MA-069 | 3 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040102071 | 3 / 345 | 3 / 345 | exact | pass ×3 |
| 90-KWE-26MA-081 | 2 | ma_no_period_v1 | ROBERT BOSCH.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040103342 | 2 / 69 | 2 / 69 | exact | pass ×2 |
| 90-KWE-26MA-111 | 7 | ma_no_period_v1 | bosch bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040105313 | 8 / 846 | 8 / 846 | exact | pass ×7 |
| 90-KWE-26MA-142 | 3 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040108220 | 3 / 240 | 3 / 240 | exact | pass ×3 |
| 90-KWE-26MA-177 | 7 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040110434 | 8 / 976 | 8 / 976 | exact | pass ×7 |
| 90-KWE-26MA-224 | 5 | ma_no_period_v1 | robert bosh.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040113525 | 6 / 510 | 6 / 510 | exact | pass ×5 |
| 90-KWE-26MA-277 | 18 | ma_no_period_v1 | ROBERT BOSCH.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040116093 | 20 / 1437 | 20 / 1437 | exact | pass ×18 |
| 90-KWE-26MA-312 | 11 | ma_no_period_v1 | ROBERT BOSCH.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040119501 | 12 / 1649 | 12 / 1649 | exact | pass ×11 |
| 90-KWE-26MA-327 | 8 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040121310 | 9 / 804.8 | 9 / 804.8 | exact | pass ×8 |
| 90-KWE-26MA-381 | 2 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040122986 | 2 / 393 | 2 / 393 | exact | pass ×2 |
| 90-KWE-26MA-421 | 4 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040125241 | 4 / 529 | 4 / 529 | exact | pass ×4 |
| 90-KWE-26MA-463 | 17 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / OCR (empty layer) | 122040128973 | 18 / 1651.9 | 18 / 1651.9 | exact | pass ×17 |
| 90-KWE-26MA-513 | 11 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / **OCR (mojibake layer)** | 122040131283 | 14 / 1252 | 14 / 1252 | exact | pass ×11 |
| 90-KWE-26MA-569 | 7 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / **OCR (mojibake layer)** | 122040134551 | 8 / 834.3 | 8 / 834.3 | exact | pass ×7 |
| 90-KWE-26MA-609 | 8 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / **OCR (mojibake layer)** | 122040137793 | 9 / 1104.3 | 9 / 1104.3 | exact | pass ×8 |
| 90-KWE-26MA-660 | 9 | ma_no_period_v1 | 2018_001.pdf | kwe_sea_waybill_v1 / **OCR (mojibake layer)** | 122040141142 | 12 / 1126.4 | 12 / 1126.4 | exact | pass ×9 |
| 90-KWE-26MA-689 | 3 | ma_no_period_v1 | robert bosch.pdf | kwe_sea_waybill_v1 / **OCR (mojibake layer)** | 122040143706 | 4 / 216.9 | 4 / 216.9 | exact | pass ×3 |
| 90-KWE-26MA-721 | 8 | ma_no_period_v1 | 2986_001 (1).pdf | kwe_sea_waybill_v1 / **OCR (mojibake layer)** | 122040146602 | 8 / 320.8 | 8 / 320.8 | exact | pass ×8 |

Independent checks (`verify_inv.json`, `reconcile.json`):
- HS is present on all 4739 lines, and the per-line HS sequence equals the printed `HS CODE` for every INV.
- INV pkg/GW equals the printed packing summary for 184/184.
- Origin is filled on every line.
- No RB unique key in this batch has two number segments (DE keys are 9 digits, JP keys are 13 digits `9843…001`), so the concat rule was not exercised.
- Every BL's invoice-ref list equals the folder's INV set.
- JP: all 20 BL pkg/GW values (OCR) equal the INV sums exactly.

## Needs human check

1. **90-C-26MA-008: the same RB is on two invoices.** RB 110936597 (Corrug. brown box, 11.604 kg) appears on INV 2120394532 (1 pkg) and on 2120394533. INV sum 27 / 2001.44 vs BL 26 / 1989.837; with the duplicate removed the sum is 26 / 1989.836, which equals the BL. Shots: `shots/008_*`.
2. **90-C-26MA-036: the same RB is on two invoices.** RB 111292965 (Packing Set 1140X970X620, 83.5 kg) appears on INV 2120422517 (1 pkg) and on 2120422518. INV sum 33 / 2884.531 vs BL 32 / 2801.033; with the duplicate removed the sum is 32 / 2801.031, which equals the BL. Shots: `shots/036_*`.
   - For 008 and 036, each invoice's value is correct for that PDF. Whether to zero out one copy is a business decision, so the extractor left the invoice counts unchanged.
3. **OCR rule deviation: 6 KWE waybills with a non-empty but garbled text layer** (513, 569, 609, 660, 689, 721). The embedded layer is the scanner's CJK OCR over English text, so it is unusable. These were OCR'd even though the layer is not empty. This needs sign-off because the rule is "OCR only when the text layer is empty". All 6 match the INV sums exactly. Shots: `shots/{513,569,609,660,689,721}_KWE_seawaybill_mojibake_layer_OCR_p1.png`.
4. All 20 JP BLs are OCR-derived: 14 have an empty layer and 6 have a garbled layer. Waybill numbers and pkg/GW are corroborated by the INV sums and the waybill's INV refs, but they were not read from a text layer.

## FYI (no action expected)

- DE GW rounding: INV sums vs BL differ by ≤0.013 kg in 12 folders (007, 037, 038, 039, 040, 130, 131, 132, 191, 192, 193, 263). Packages are exact.
- COSCO 【重要通知】: EVER ACE 1384-017E skips Taipei Port, discharges at KHH (ETA 2026-05-07), and continues to TBP on the feeder UNI-PROMOTE 0235-616B (ETA 2026-05-13). As extracted, 192 and 193 have POD Taipei Port with ETA 2026-05-13, and 260, 261, 262 have POD Kaohsiung with ETA 2026-05-07. Shots: `shots/192_*`, `shots/260_*`.
- KWE waybills have no ETA (the ETD / on-board date is extracted). Vessel is empty on 721 (OCR). Some OCR voyage reads are doubtful (381, 569, 312). These are informational fields only.

## Materials

- `InvoiceExtract_Result.xlsx`: Summary (184 rows, BL columns filled) / Lines (4739) / meta
- `BLExtract_Result.xlsx`: 39 BL, 0 failed
- `json/<folder>/INV_*.json`, `json/<folder>/BL_*.json`
- `reconcile.json` (BL vs INV sums, shared RB), `verify_inv.json` (HS / packing cross-check)
- `shots/`: needs-check items only

## CLI

```bash
export PYTHONPATH=src:vendor
python3 -m invoice_extractor "<root>/RBDEsea/90-C-26MA-007" … --out InvoiceExtract_Result.xlsx   # directory args are not recursive: pass each folder
python3 -m invoice_extractor --doc-type bl <BL files> --out BLExtract_Result.xlsx
```
