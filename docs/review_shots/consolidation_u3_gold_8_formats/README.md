# Consolidation U3 — gold for the 8 formats that had no tests

Branch `consolidate/u3-gold-8-formats` (on top of U2). Test-only: **no `src/` change.**

## What changed
- `tests/test_private_gold.py`: 16 single-document checks (`extract_invoice` / `extract_bl`) against private gold `/workspace/invoice-samples/gold/cov8.json`. Invoices compare every Result field (Summary + Lines, floats rounded to 6 dp); BLs compare BL no., packages, G.W., invoice refs.
- Inputs copied (minus .msg/.png) into `/workspace/invoice-samples/regression/cov8/` (13 case folders), all in the manifest.

| Format | Documents frozen |
|---|---|
| aichi_electric_v1 | 2 invoices |
| bhc_manual_inv_v1 | 2 invoices (one with lines excluded, see issues #1) |
| hitachi_asia_hitt_v1 | 1 invoice |
| ohizumi_dongguan_v1 | 4 (2 PDF + 2 xls twins; one PDF with total_pkg excluded) |
| oukai_v1 | 1 xls (total_quantity excluded) |
| sumitronics_hk_v1 | 2 (PDF + xlsx; xlsx pkg/GW excluded) |
| dhl_danmar_bl_v1 | 2 BL |
| nippon_express_awb_v1 | 2 AWB — **enabled but unaudited: please review** |

Gold = current main output, each value checked by the Invoice bot against the document text. Anything that looked wrong was **not** frozen; it is listed with the document value in `/workspace/invoice-samples/review/consolidation_u3/issues.md` (7 items: 3 rule defects, 1 document inconsistency, 1 cosmetic, 1 AWB-vs-PL difference, 1 scope question).

## Evidence
- `pytest tests/test_private_gold.py` → 16 passed. With no store: fails locally, skipped in CI.
- Not added to `regression_batches.py`: run through the pairing pipeline these folders produce 31 hard findings that are pairing noise (PL files and xls twins counted as separate rows), which would make the batch run fail permanently. The single-document gold is the stricter check.
- No `src/` change → existing regression unchanged by construction.
