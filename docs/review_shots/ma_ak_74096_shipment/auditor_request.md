# Auditor request — MA AK Billing HU dedupe (AK00074096 / 097 / 098)

**Scope:** three Robert Bosch GmbH Mobility Aftermarket Billing Document invoices, one shipment (same consignment 300037751, billed 02.11.2026). Layout is existing `ma_ak_billing_v1` (no new format_id). The user reported that the latest portable computed packages and G.W. wrongly when this set was run together.

**Branch:** `feature/ma-ak-hu-dedupe` (not pushed / not merged). Commits: see `git log --oneline feature/ma-ak-hu-dedupe`.

**Pack:** this folder.
- `INV_AK0007409x.json`: extracts **after** `shipment_first` (what Result should show). `_printed_pkg_gw` is the per-PDF unique-HU total before cross-invoice dedupe. `_hard` is the hard-check.
- `pages/`: every invoice page at 120 dpi.
- `crops/`: Marking pages plus the user's Marking screenshots.

## Root cause (for context)

1. Newer AK invoices print **`Gross HU Weight`**. The old HU regex required `Gross <number> KG`, so no handling unit was matched.
2. The format then fell back to each PDF's printed `Total Num of packages` / `Total Gross Weight`. Those per-file figures happen to equal that file's unique HUs, but **`meta.packing_units` was never set**.
3. `shipment_first` therefore never ran. Running the three files together **double-counted** the 10 HUs that appear on both AK00074097 and AK00074098 → **50 / 9,927.56** instead of **40 / 8,790.28**.

The typographic “RB + number + Gross” rule is unchanged: only the first line of the Marking block has the literal `RB`; later 18-digit HU ids without `RB` still count; POS-no / Net Val lines do not; unique key is the 18-digit HU alone (no two-segment concat). First occurrence wins, including across invoices of the same shipment.

## Please verify

1. **Per invoice (printed unique HU totals, before shipment_first):**
   - AK00074096: 30 packages / 7,653.000 kg (matches its printed Total Num of packages / Total Gross Weight). 24 lines, Net value 1,196,827 TWD, Incoterms FOB Malaysia. All Commodity Codes present.
   - AK00074097: 10 / 1,137.280 (matches its printed totals). 8 lines, 347,990 TWD, FCA Bosch Plant.
   - AK00074098: 10 / 1,137.280 (matches its printed totals). 1 line, 45,936 TWD, FCA Bosch Plant.
2. **Shipment union (hand-counted unique 18-digit HUs + Gross HU Weight, first wins):** 40 packages / 8,790.28 kg. AK00074096's 30 HUs are disjoint from the other two; AK00074097 and AK00074098 have **the same 10 HUs** (same Gross on each).
3. **Result after shipment_first** (invoice no. order):
   - AK00074096: **40 / 8,790.28** plus Summary note (printed 30 / 7653).
   - AK00074097 and AK00074098: **0 / 0** plus note “shipment pkg/GW (deduped) on AK00074096; printed pkg/GW 10 / 1137.28”.
   - Line qty and amounts are not touched.
4. **Printed totals vs union:** each invoice's printed Total Gross Weight equals that invoice's unique-HU sum. The printed 10 / 1,137.280 on *both* 097 and 098 is the same 10-HU list, not a second batch — adding the three printed totals (50 / 9,927.56) is wrong.
5. **No new format_id.** Older AK invoices that still print `Gross 5.000 KG` (no “HU Weight”) must keep their previous pkg/GW. Regression on 248 other MA invoices (WithPeriod / NoPeriod / earlier AK) was unchanged.

Please reply per invoice: pass / fix (with field and gold value).
