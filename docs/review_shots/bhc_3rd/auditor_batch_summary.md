# BHC 3rd data (cases 1–9) — FormatSOP audit pack

**Date:** 2026-09-24 (Asia/Taipei)  
**Branch:** `feature/formatsop-bhc-3rd` (do **not** merge main until Auditor accept; no portable)  
**Input:** `/home/box/Downloads/BHC-batch-0924/3rd data/case 1 .. case 9` (`.msg` ignored)  
**Review pack:** `/workspace/InvoiceExtractor/docs/review_shots/bhc_3rd/`

## Format IDs in this pack

| format_id | new/existing | Role |
|-----------|--------------|------|
| `suzhou_aichi_v1` | **NEW** | 苏州爱知 SATJG… combined INV+PKL (OCR) |
| `marubeni_tetsugen_v1` | existing | Marubeni copper tube INV+PL (OCR) |
| `sumitronics_hk_v1` | **NEW** | Sumitronics HK PCBA INV+PL (+xlsx twin) |
| `bhc_my_hub_v1` | existing | MY-HUB INV 9027757002 + PKL overlay |
| `bhc_manual_inv_v1` | **NEW** | TW-MANUAL damage-replacement INV |
| `dunan_v1` | **NEW** | 浙江盾安 INV (+PKL/xlsx) |
| `ohizumi_dongguan_v1` | **NEW** | 东莞大泉 Ohizumi INV+PL (+xls) |
| `oukai_v1` | **NEW** | 常州欧凯 stepper (.xls primary) |
| `hitachi_asia_hitt_v1` | **NEW** | Hitachi Asia / HITT USDI… (≠ hitachi_gls) |
| `nidec_v1` | existing | NIDEC VKT26069 |
| `hippopo_arrival_v1` | **NEW** | Hippopo 到貨通知書 (CPSE/P076…) |
| `dhl_danmar_bl_v1` | **NEW** | DHL/Danmar ocean B/L (NGOA…) |
| `tvl_hbl_v1` | existing | TVL HBL SHAKEL… |
| `china_progress_bl_v1` | **NEW** | China Progress 提单 (NBSE…) |

Also: real **`.xls` support** via `xlrd` (`excel/xlrd` backend) in `excel_text.py`.

## Primary extract table

| case | file | doc type | format_id | invoice_no | amount | currency | lines | pkg | GW | BL No. / pkg / GW | hard | backend | notes |
|------|------|----------|-----------|------------|--------|----------|-------|-----|-----|-------------------|------|---------|-------|
| 1 | SATJG26010.pdf | INV+PKL | `suzhou_aichi_v1` **NEW** | SATJG26010 | 40875.00 | USD | 2 | 7 | 4121 | CPSE26090643 / 7 / 4121 | pass | ocr/tesseract | OCR; amount=sum(lines); confirm PN TW10002/TW10005 |
| 1 | 到貨通知.pdf | arrival | `hippopo_arrival_v1` **NEW** | — | — | — | — | — | — | CPSE26090643 / 7 PLTS / 4121 | pass | pdftotext | paired into INV Summary BL cols |
| 2 | (JCH26-09M1) Invoice, PL.pdf | INV+PL | `marubeni_tetsugen_v1` | JCH26-09M1 | 28201.12 | USD | 1 | 2 | 1424 | NGOA23906 / 2 / 1424 | pass | ocr/tesseract | |
| 2 | Bill Of Lading - NGOA23906.pdf | B/L | `dhl_danmar_bl_v1` **NEW** | — | — | — | — | — | — | NGOA23906 / 2 CASE / 1424 | pass | pdftotext | ≠ dhl_lcl_arrival |
| 3 | ST0826170 INV&PL.pdf | INV+PL | `sumitronics_hk_v1` **NEW** | ST0826170 | 145584.80 | USD | 4 | 36 | 6937.4 | P076ADNE2608 / 36 / 6937.4 | pass | pdftotext | xlsx twin same totals |
| 3 | ST0826170 INV&PL.xlsx | INV+PL | `sumitronics_hk_v1` | ST0826170 | 145584.80 | USD | 4 | — | — | same BL | pass | excel/openpyxl | cross-check OK |
| 3 | 到貨通知.pdf | arrival | `hippopo_arrival_v1` | — | — | — | — | — | — | P076ADNE2608 / 36 / 6937.4 | pass | pdftotext | 18+18 PLTS summed |
| 4 | BHCWHYTW2609004_INV_9027757002.PDF | INV | `bhc_my_hub_v1` | 9027757002 | 79095.76 | USD | 15 | 221 | 2607.53 | SHAKEL26971792 / 1×20GP / 2608.83 | pass | pdftotext | PKL overlay; BL≠invoice pkg |
| 4 | INV#TW-MANUAL-015-BHCWHQA260915A.pdf | INV | `bhc_manual_inv_v1` **NEW** | TW-MANUAL-015 | 83.00 | USD | 1 | soft | soft | SHAKEL26971792 / 1 / 2608.83 | pass | pdftotext | no commercial value; QA PKL soft |
| 4 | 20260918102712-0001.pdf | HBL | `tvl_hbl_v1` | — | — | — | — | — | — | SHAKEL26971792 | pass | ocr/tesseract | scan |
| 5 | 标准_结汇发票FT00044266.pdf | INV | `dunan_v1` **NEW** | DA15199998/2/5/52 | 45545.58 | USD | 7 | 8 | 3326 | NBSE26090042 / 8 / 3326 | pass | pdftotext | xlsx twin same amt; pkg from PKL |
| 5 | 44266提单.pdf | B/L | `china_progress_bl_v1` **NEW** | — | — | — | — | — | — | NBSE26090042 / 8 PALLETS / 3326 | pass | pdftotext | |
| 6 | (發票)…东莞大泉.pdf / .xls | INV+PL | `ohizumi_dongguan_v1` **NEW** | OHIZUMI-26575OUT | 8543.54 | USD | 5 | 22 | 267.86 | CPSE26090724 / 22 / 267.86 | pass | pdf + excel/xlrd | xls preferred for GW |
| 6 | 到貨通知.pdf | arrival | `hippopo_arrival_v1` | — | — | — | — | — | — | CPSE26090724 / 22 CARTONS / 267.86 | pass | pdftotext | |
| 7 | OK20260921.xls | INV+PL | `oukai_v1` **NEW** | OK20260921 | 14755.00 | USD | 3 | 83 | 830 | SHAKEL26972017 / 83 / 830 | pass | excel/xlrd | scan INV unreadable; line qty sum 20750 vs vendor Total 10750 — used sum(lines); Auditor confirm |
| 7 | 20260923094251-0001.pdf | HBL | `tvl_hbl_v1` | — | — | — | — | — | — | SHAKEL26972017 / 83 / 830 | pass | ocr/tesseract | |
| 8 | USDI4105369.pdf | INV | `hitachi_asia_hitt_v1` **NEW** | USDI4105369 | 6936.92 | USD | 5 | soft | soft | — | pass | pdftotext | PACKING LIST (BOSCH) content ≠ motors (bebicon) — not used |
| 8 | BL.pdf | B/L | — | — | — | — | — | — | — | — | **needs_gold** | ocr/tesseract | OCR too poor (LITCON); figure shows ~2 PALLETS / 1174 KGS |
| 9 | BHC-TW_VKT26069_…draft.pdf | INV+PL | `nidec_v1` | VKT26069 | 83493.00 | USD | 4 | 31 | 7498.7 | — | pass | pdftotext | |
| 9 | doc124112…pdf | B/L | — | — | — | — | — | — | — | GLHAKEL2609051? | **needs_gold** | ocr/tesseract | OCR too poor (Global Line); not matched |

## Skipped / needs_gold

| case | item | reason |
|------|------|--------|
| all | `*.msg` | ignored per FormatSOP |
| 7 | scan PDF as INV source | empty text / not invoice layout; use `.xls` |
| 8 | `BL.pdf` extract | OCR quality too poor to extract BL No./pkg/GW reliably |
| 8 | `PACKING LIST (BOSCH).pdf` | text shows bebicon compressors, not HITT motors on USDI invoice — do not overlay |
| 9 | `doc124112…pdf` BL | OCR too poor; no reliable format match |
| 4 | QA PKL pkg/GW | TOTAL line not parsed by generic packing overlay (1 carton / 1.0 kg on figure) — soft-missing OK |
| 5/6 | PKL-only pair rows | expected `needs_gold` when run as invoice (no amount); use INV+overlay |

## Materials

Absolute base: `/workspace/InvoiceExtractor/docs/review_shots/bhc_3rd/`

- JSON: `case*_*.json` (+ `case8_bl_needs_gold.json`, `case9_bl_needs_gold.json`)
- Shots: `case*_*.png` (key INV / PKL / BL pages)
- This summary

## Auditor focus

1. Hard pass ≠ final accept — confirm figure vs JSON (invoice_no, labeled total, LINE/qty, Gross GW, Incoterm, currency, BL three fields).
2. **case1 OCR**: PN/amount/7 pallets / 4121 GW vs figure.
3. **case7**: vendor Total qty 10750 vs line sum 20750 — confirm which is correct on figure; amount 14755 matches line amounts.
4. **case8**: INV OK; BL needs_gold; ignore mismatched PACKING LIST.
5. **case9**: NIDEC INV OK; BL scan needs_gold.
6. BHC HS soft-missing OK.
7. Reply per row: `pass` | `conflict` | `needs_gold`.

## CLI

```bash
python -m invoice_extractor "/path/to/case N" --out out.json
python -m invoice_extractor --doc-type bl path.pdf --out bl.json
```
