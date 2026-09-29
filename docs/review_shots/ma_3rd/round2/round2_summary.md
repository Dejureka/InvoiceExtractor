# MA 3rd — Round 2 (Auditor review of c7a216d)

**Date:** 2026-09-29 (Asia/Taipei) · **Branch:** `feature/ma-3rd` (not merged)  
**Final scope (user, via Auditor):** (1) only fields that exist in `InvoiceExtract_Result` are extracted — BL = BL No. / BL Packages / BL G.W.; (2) shared RB across invoices of one MA shipment: deduped shipment pkg/GW on the first invoice, others 0 (mode B); (3) garbled-layer OCR kept with backend logging + SOP wording.

## 1. Result-fields-only rule (BL)

`InvoiceExtract_Result.xlsx` columns checked: Summary = Invoice No. / Packages / Package Mode / G.W. / Incoterms / Invoice Value / LINE / QTY / Invoice Currency / BL No. / BL Packages / BL G.W.; Lines = PN / Des / Qty / Unt / Amt / UoM / Co / HS code / N.W. / InvoiceNumber / Currency. None of vessel, voyage, ETA/ETD, CBM is a Result column, so none is kept.

| format | before (c7a216d) | after |
|---|---|---|
| `cosco_arrival_v1` (19 DE) | bl_no, mbl_no, pkg, GW, vessel, voyage, ETA, POD, POL, container/seal, FCL, CBM, invoice refs, shipper/consignee/notify, forwarder | **bl_no, packages, gross_weight_kg** (container row still used internally to cross-check pkg/GW) |
| `kwe_sea_waybill_v1` (20 JP) | bl_no, hbl_no, pkg, GW, vessel, voyage, ETD, CBM, POL, POD, invoice refs, shipper/consignee, forwarder, LCL | **bl_no, packages, gross_weight_kg** |

Values of the three kept fields are unchanged for all 39 BLs (DE 19/19, JP 20/20 = Auditor-verified print). The earlier Round 2 ETD (177/689) and CBM (312/513) fixes are dropped with the fields. Older audited BL formats are untouched. The Round 1 informational conflicts on 069/177/312/327/381/513/569/689/721 no longer exist because those fields are no longer output.

## 2. Shared RB — shipment-level count on the first invoice (user decision: mode B)

Rule: in an MA shipment (same folder / same BL No.) with several invoices where an RB key repeats across them, the shipment's RB-deduped pkg / GW goes on the first invoice (sorted by invoice number) and every other invoice gets pkg / GW = 0. Line qty / amounts unchanged. Each affected invoice gets an Excel note on the Summary Packages and G.W. cells (also `header.summary_note`, `meta.notes`, `meta.shipment_packing`). Shipments without a repeated RB keep each invoice's own printed pkg / GW. Implemented generically: `meta.packing_units` (MA formats) + `pairing.dedupe_shared_packing_units` (`SHARED_RB_MODE = "shipment_first"`).

| folder | invoice | before (printed) pkg / GW | after pkg / GW | Summary note |
|---|---|---|---|---|
| 008 | 2120394532 | 1 / 11.604 | **26 / 1989.836** | shipment pkg/GW (deduped) 26 / 1989.836 on this first invoice (2 invoices, shared RB 110936597); printed pkg/GW 1 / 11.604 |
| 008 | 2120394533 | 26 / 1989.836 | **0 / 0** | shipment pkg/GW (deduped) on 2120394532; printed pkg/GW 26 / 1989.836 |
| 008 | folder Σ | 27 / 2001.44 | 26 / 1989.836 | BL 26 / 1989.837 (Δ −0.001 rounding) |
| 036 | 2120422517 | 1 / 83.5 | **32 / 2801.031** | shipment pkg/GW (deduped) 32 / 2801.031 on this first invoice (3 invoices, shared RB 111292965); printed pkg/GW 1 / 83.5 |
| 036 | 2120422518 | 3 / 313 | **0 / 0** | shipment pkg/GW (deduped) on 2120422517; printed pkg/GW 3 / 313 |
| 036 | 2120422519 | 29 / 2488.031 | **0 / 0** | shipment pkg/GW (deduped) on 2120422517; printed pkg/GW 29 / 2488.031 |
| 036 | folder Σ | 33 / 2884.531 | 32 / 2801.031 | BL 32 / 2801.033 (Δ −0.002 rounding) |

Only these two shipments have a repeated RB in all 39 folders; the other 179 invoices keep their printed pkg / GW (compared field-by-field against Round 1).

## 3. Garbled-layer OCR (approved)

- Detection unchanged (`text_layer_looks_mojibake`, same thresholds; only 513/569/609/660/689/721 of 424 sample PDFs).
- Backend logged: `meta.text_backend = ocr/tesseract+prefer_over_stale_layer+mojibake_layer`; CLI warning "OCR used (…+mojibake_layer): PDF text layer is unreliable (garbled scanner CJK-mode OCR over a Latin page)"; Python log `OCR backend … used for <file> (text layer mojibake)`.
- SOP / README wording: "OCR when the text layer is empty or unreliable".

## 4. Needs-check (Round 2)

Shared RB only: `../shots/008_INV2120394532_sharedRB110936597_p3.png`, `../shots/008_INV2120394533_sharedRB110936597_p23.png`, `../shots/008_BL_COSU6431163410_total26_p1.png`, `../shots/036_INV2120422517_sharedRB111292965_p3.png`, `../shots/036_INV2120422518_sharedRB111292965_p5.png`, `../shots/036_BL_COSU6438665680_total32_p2.png`.

`../reconcile.json` / `../verify_inv.json` are Round 1 checks (pre-dedupe).
