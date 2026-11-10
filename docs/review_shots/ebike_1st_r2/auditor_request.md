# Auditor request — eBike 1st r2 (unit-price rule change)

**Scope:** Same 18 AX Billing invoices as `docs/review_shots/ebike_1st/` (AX00011132–AX00011149, Robert Bosch Energy and Body Systems Kft, 27.08.2026, EUR, FCA Miskolc). This pack is a **rule change only**: how **unit price (Unt)** is derived. Qty, amount, HS policy, packages / G.W., AX00011144 Copy, and the AX00011148 line-NW note are unchanged.

**Branch:** `feature/ebike-fixes` (not pushed / not merged).

**Pack:** this folder (`pages/` and `crops/` are the same images as r1). Compare JSONs against r1 if you want a diff; only `unit_price` (and the now-absent `pricing_unit`) should change on the lines.

## What changed

Almost every printed unit price on this layout is **per Pricing Unit 100 PC**. r1 stored that printed figure as Unt and kept `pricing_unit=100` so hard_check did `qty × unit_price / 100`.

The user (2026-11-10) asked that Unt be **amount / qty**, rounded to 6 decimal places (same rounding as SOE derived unit prices), with **qty and amount left as printed**. The printed per-100 price is no longer parsed as unit price. `pricing_unit` is left unset, so hard_check uses per-1 (`qty × unit_price ≈ amount`).

Examples (printed per-100 → new Unt):

| Invoice | PN | Qty | Amount (printed) | r1 Unt (per 100 PC) | r2 Unt (amount/qty) |
|---------|----|-----|------------------|---------------------|---------------------|
| AX00011135 | EB12.100.015-1CF | 1,100 | 2,663.43 | 242.13 | 2.4213 |
| AX00011139 | EB11.900.018-VE4 | 25 | 4,505.61 | 18,022.42 | 180.2244 |
| AX00011144 | EB12.100.076-VE4 | 70 | 6,398.88 | 9,141.25 | 91.412571 |

## Please verify

1. **Unit price** on every line is amount / qty (6 d.p.), not the printed per-100 figure. Qty and Net Value / amount still match the page.
2. Previously confirmed rules still hold: HS soft when Commodity Code is unprinted (AX00011144 / 11145 / 11148 item `EB13.900.025-VE4`); no shipment_first; AX00011148 `EB13.900.029-VE4` NW kept as 8,292 kg with `line_nw_exceeds_total_nw`; AX00011144 Copy is a real invoice.

Hard-check: **18 / 18 pass**.

Please reply per invoice: pass / fix (with field and gold value).
