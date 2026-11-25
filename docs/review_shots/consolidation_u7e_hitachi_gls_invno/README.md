# Consolidation U7e — hitachi_gls: invoice no. / date by position, not by "MEH"

Branch `consolidate/u7e-hitachi-gls-invno` (on top of U7d). FormatSOP bug fix (fragility audit #1).

## What changed
- Invoice no. + date come from the value row under the `Invoice No. … Date` label row (`<consignee> <no> <MON. DD, YYYY>`), shape `[A-Z]{1,6}\d[0-9A-Z-]{3,}` — no vendor prefix. Same-line `Invoice No.: X` stays as second rule; the date can also be read right after the found number.
- A number outside the MEH series is still output but marked via `fallback()` → `needs_gold_fields=["invoice_no"]` (a person confirms the new series).
- GRAND TOTAL reads the currency symbol: `J¥` → JPY (as before), `US$` → USD. Currency was hard-coded JPY.
- Not changed: classifier score, incoterm (`FOB SHIMIZU` only), line-item rules.

## Value changes (corpus 448 docs + regression)
Regression 8 batches: diff 0 (all 5 MEH invoices identical). Corpus: **1 document**:

`bhc-plan/inbox/20261115_KLG-T26ZCQL/att/DC76K507.pdf` (checked against the PDF text):

| Field | Before | After | PDF |
|---|---|---|---|
| invoice_no | empty | DC76K507 (needs_gold: new series) | `Invoice No. … DC76K507` ✔ |
| invoice_date (not in Result) | empty | 2026-11-06 | `NOV. 06, 2026` ✔ |
| amount | empty | 2449.00 | `GRAND TOTAL: 145 PCS US$2,449.00` ✔ |
| total_quantity | empty | 145 | ✔ |
| currency | **JPY (wrong)** | USD | `US DOLLAR` / `US$` ✔ |
| total_pkg / GW | 17 / 121.93 | unchanged | `TOTAL : 17 … 145 109.4 121.93 1.446` (CARTONS) ✔ |

Still needs a person: **0 line items** (this USD service-parts layout — `01 AIR-PULLY PARTS 8 PCS 14.17 113.36` + `ORDER P#` lines — differs from the MEH tables) and incoterm `FOB JAPAN` not read. Per the needs_gold triage this is a new layout: fill manually, run FormatSOP when about 3 samples exist.

Tests: `tests/test_hitachi_gls_header.py` (synthetic: MEH unchanged; other series read + flagged; US$).
