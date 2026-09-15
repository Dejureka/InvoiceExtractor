# BHC OCR-scan FormatSOP — AuditSOP pack

**Date:** 2026-09-16 (Asia/Taipei)  
**Branch:** `ocr-experiment` (do **not** merge main; portable-latest untouched)  
**Scope:** empty-text-layer **scans** under `/workspace/bhc_cases_round/bhc/` cases 2/4/5/7/8.  
**OCR backend:** `ocr/tesseract` (fallback when pdftotext layer empty). Text-layer INV controls use `pdftotext -layout`.

## Format IDs in this pack

| format_id | Role | Samples |
|-----------|------|---------|
| `marubeni_tetsugen_v1` | Combined INV+PL scan | case2 `(JCH26-08M1) Invoice, PL.pdf` |
| `shanghai_nature_v1` | INV (+ optional PKL) scan | case7 `invoice309.pdf` / `packing309.pdf` |
| `tvl_hbl_v1` | TVL / Trans Van Links **HBL** scan | case7 `20260903091515-0001.pdf`, case8 `20260904232648-0001.pdf` |
| `bhc_my_hub_v1` | Text INV + **OCR PKL overlay** (pkg/GW) | case4×3 PKL, case5 PKL (+ text INV controls) |

## Hard verdicts (primary extracts)

| case | file / row | format_id | backend | key fields | hard |
|------|------------|-----------|---------|------------|------|
| 2 | `(JCH26-08M1) Invoice, PL.pdf` | `marubeni_tetsugen_v1` | ocr/tesseract | inv=`JCH26-08M1` amt=67930.24 USD lines=2 pkg=5 GW=3560 | **pass** |
| 4 | text INV `…_INV_9027451705.PDF` | `bhc_my_hub_v1` | pdftotext -layout | inv=`9027451705` amt=579919.92 lines=8 (no pkg/GW alone) | **pass** |
| 4 | `PKL_TA2608B2-3253,TA2608B3254.pdf` | overlay via `parse_packing_pkg_gw` | ocr/tesseract | pkg=**39** GW=**6389.94** (PKL-only extract needs_gold) | overlay OK |
| 4 | `PKL_TA2608B2-3255.pdf` | same | ocr/tesseract | pkg=**40** GW=**6860.8** | overlay OK |
| 4 | `PKL_TA2608B2-3256.pdf` | same | ocr/tesseract | pkg=**20** GW=**3844.8** | overlay OK |
| 4 | **INV + 3×PKL OCR sum** | `bhc_my_hub_v1` | inv text + pkl OCR | pkg=**99** GW=**17095.54** (39+40+20 / sum GW) | **pass** |
| 5 | text INV `…_INV_9027451746.PDF` | `bhc_my_hub_v1` | pdftotext -layout | inv=`9027451746` amt=134950.29 lines=5 | **pass** |
| 5 | `PKL_TA2608B2-3257, TA2608B3258.pdf` | overlay | ocr/tesseract | pkg=**33**; **GW soft-missing** (OCR footer noisy) | pkg OK / GW soft |
| 5 | **INV + PKL OCR** | `bhc_my_hub_v1` | inv text + pkl OCR | pkg=33, GW=null (figure shows **6052.14**) | **pass** (GW soft) |
| 7 | `invoice309.pdf` | `shanghai_nature_v1` | ocr/tesseract | inv=`NBT309` amt=7478.10 USD lines=6 FOB SHANGHAI | **pass** |
| 7 | `packing309.pdf` | `shanghai_nature_v1` / overlay | ocr/tesseract | pkg/GW soft-missing (noisy OCR); BL has 1 PLT / 231 | soft OK |
| 7 | `20260903091515-0001.pdf` | `tvl_hbl_v1` | ocr/tesseract | see **BL three fields** below | **pass** |
| 8 | `20260904232648-0001.pdf` | `tvl_hbl_v1` | ocr/tesseract | see **BL three fields** below | **pass** |
| 8 | text INV+PKL control | `bhc_my_hub_v1` | pdftotext -layout | inv=`9027666020` amt=119636.08 pkg=326 GW=3469.5 — **already audited** in `docs/review_shots/bhc_cases_1368/` | **pass** (control) |

PKL-only rows flagged `needs_gold` when run as invoice extracts (no invoice_no/amount) — expected; use paired overlay / `pkl_overlay` in JSON.

## BL three fields (Summary: `BL No.` / `BL Packages` / `BL G.W. (kgs)`)

| case | file | format_id | **BL No.** | **BL Packages** | **BL G.W. (kgs)** | unit / notes |
|------|------|-----------|------------|-----------------|-------------------|--------------|
| 7 | `20260903091515-0001.pdf` | `tvl_hbl_v1` | **SHAKEL26970898** | **1** | **231.0** | PALLET; vessel GLORY OCEAN / 2636S; POL Shanghai → POD Keelung |
| 8 | `20260904232648-0001.pdf` | `tvl_hbl_v1` | **SHAKEL26770270** | **1** | **3469.5** | unit **20GP** (container face); invoice cartons=326 / GW=3469.5 from text PKL — BL Packages ≠ invoice Packages |

Never overwrite invoice Packages/G.W. with BL columns.

## Materials (this folder)

Absolute base: `/workspace/InvoiceExtractor/docs/review_shots/bhc_ocr_scans/`

- JSON: `case2_*.json`, `case4_*.json`, `case5_*.json`, `case7_*.json`, `case8_*.json`
- Shots: `*_p1.png` (+ case2 `*_p2_pkl_gw.png` for packing TOTAL GW)
- This summary + `auditor_message.txt`

## Auditor focus

1. **OCR vs figure**: invoice_no, labeled total, line count/qty, Gross GW, Incoterm, currency.
2. **case2 Marubeni**: Total US$67,930.24; PKL TOTAL 5 CASE / 3,560.0 kgs (p2 shot).
3. **case4**: three OCR PKL overlays sum to 99 / 17095.54 — match text INV + prior CEVA arrival WEB260166448.
4. **case5**: confirm figure GW **6052.14** (OCR soft-miss); pkg 33 from `Pallets no. 1-33`.
5. **case7 Nature**: 6 heating-belt lines; soft-missing pkg/GW OK; HBL SHAKEL26970898 / 1 PALLET / 231.
6. **case8**: OCR HBL only for new work; text INV/PKL already accepted in bhc_cases_1368 — check BL three fields beside control.
7. Hard pass ≠ final accept. Reply per row: `pass` | `conflict` | `needs_gold`.

## CLI reminders

```bash
python -m invoice_extractor path.pdf --out out.json
python -m invoice_extractor --doc-type bl hbl.pdf --out bl.json
# INV+PKL pairing (GUI or multi-PDF) overlays OCR PKL pkg/GW onto text INV
```
