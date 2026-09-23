# MA-747 (90-S-26MA-747) — FormatSOP audit pack

**Date:** 2026-09-23 (Asia/Taipei / PT)  
**Source root (on disk, not re-downloaded):** `/home/box/Downloads/MA-747/90-S-26MA-747/`  
**Branch:** `feature/formatsop-ma-747`  
**Hard pass ≠ final accept** — Auditor must review JSON + page shots.

## Formats

| side | format_id | notes |
|------|-----------|-------|
| FWD INV | `ma_ak_billing_v1` | `AK0006772x_INV.PDF` (5 files: 724,725,726,729,730) |
| SAP INV | `ma_ak_billing_v1` | `Invoice AK0006772x.PDF` — **byte-identical** to matching FWD PDF (md5 same) |
| BL / 到貨 | `milestone_arrival_v1` | `到貨通知 HBL005289.pdf` |

No new format_id. Extended `ma_ak_billing_v1` NOTES + filename `AK########_INV` scoring; hard_check line tol now allows 0.1% relative (Bosch Net Value vs Unit×Qty).

## Hard results (FWD = SAP content)

| invoice_no | format | amount (TWD) | pkg | GW | lines | HS miss | hard |
|------------|--------|-------------:|----:|---:|------:|--------:|------|
| AK00067724 | ma_ak_billing_v1 | 1,526,657 | 13 | 1881.55 | 37 | 0 | **pass** |
| AK00067725 | ma_ak_billing_v1 | 302,093 | 7 | 887.40 | 14 | 0 | **pass** |
| AK00067726 | ma_ak_billing_v1 | 383,464 | 6 | 909.70 | 11 | 0 | **pass** |
| AK00067729 | ma_ak_billing_v1 | 3,275,203 | 33 | 4134.17 | 52 | 0 | **pass** |
| AK00067730 | ma_ak_billing_v1 | 888,855 | 19 | 3409.35 | 51 | 0 | **pass** |

**AK00067730 note:** 3 lines have printed Net Value ≠ Unit Price×Qty by ~0.07–0.1% (e.g. 35×228=7980 vs Net 7973). Extraction trusts printed Net Value; sum(lines)=header Net value. Checker relative tol covers this.

## FWD ↔ SAP comparison

| invoice_no | amount | pkg | GW | lines | HS complete | pdf bytes |
|------------|--------|-----|----|-------|-------------|-----------|
| AK00067724 | same | same | same | same | same | identical |
| AK00067725 | same | same | same | same | same | identical |
| AK00067726 | same | same | same | same | same | identical |
| AK00067729 | same | same | same | same | same | identical |
| AK00067730 | same | same | same | same | same | identical |

## BL

| field | value |
|-------|-------|
| format_id | `milestone_arrival_v1` |
| BL No. | HBL005289 |
| Packages | 78 |
| G.W. (kgs) | 11222.17 |
| ETA | 2026-09-25 |
| Vessel / Voy | WAN HAI 287 / N077 |
| Invoice refs | AK00067724, AK00067725, AK00067726, AK00067729, AK00067730 |
| hard | **pass** |

**INV sum vs BL:** pkg 13+7+6+33+19 = **78**; GW 1881.55+887.4+909.7+4134.17+3409.35 = **11222.17** — match.

Auto-pair does not N:1 link when INV files live under `FWD INV/` and BL is in parent folder; smoke Excel `InvoiceExtract_Result_paired_fwd_bl.xlsx` uses manual `merge_bl_onto_inv` (multi-INV same BL columns).

## Materials

- `docs/review_shots/ma_747/fwd/` — JSON + p1/p2/plast PNG + `InvoiceExtract_Result.xlsx`
- `docs/review_shots/ma_747/sap/` — same
- `docs/review_shots/ma_747/HBL005289.json` + `HBL005289-1.png` + `BLExtract_Result.xlsx`
- `fwd_sap_comparison.json`
- `InvoiceExtract_Result_paired_fwd_bl.xlsx` (optional Summary BL columns)

## Auditor checklist

1. Spot-check amount = on-PDF **Net value** (not unit price).
2. GW = Marking / packing Gross (not line Net Weight).
3. Every line has Commodity Code (HS).
4. AK00067730 Brake Disc lines: Net Value vs Unit×Qty slight gap is on PDF — OK if sum matches header.
5. BL HBL005289 pkg/GW vs INV totals.
6. FWD vs SAP: expect identical extracts (same PDFs).

**Next:** call Auditor with this pack (JSON + shots). Do not treat hard pass as final accept.
