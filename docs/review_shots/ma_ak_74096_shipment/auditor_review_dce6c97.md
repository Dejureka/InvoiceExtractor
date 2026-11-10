# Auditor review — MA AK00074096 / 097 / 098 (HU dedupe)

**Verdict: all three invoices pass.**

- Branch / commit audited: `feature/ma-ak-hu-dedupe` @ `dce6c97` (not merged). Repo checkout was not switched; pytest ran from a detached worktree at `/tmp/ie_dce6c97`.
- Format: existing `ma_ak_billing_v1`. No new format_id.
- Pack: `/workspace/InvoiceExtractor/docs/review_shots/ma_ak_74096_shipment/`
- Source PDFs (rendered with `pdftoppm` at 150/200 dpi; page images, not text layers, used as truth):
  - AK00074096: `/workspace/ma_new_inv/5b496928d2ef0a916fa4dfc897a4d54ebea8473d91f7adfc8b694b84b1e48722.pdf` (9 pages)
  - AK00074097: `/workspace/ma_new_inv/cb8a392d814353bb6d1a8b73bcb32f9daac16ad5ceea09185a96f4406073706f.pdf` (4 pages)
  - AK00074098: `/workspace/ma_new_inv/c45a4ea70350b0d3a4809dffdfdcc514d9c74c7ca87265d9188ed50447755ec6.pdf` (2 pages)
- Evidence crops: `/workspace/ma_ak_74096_audit/crops/` (backup of this file is also there).
- Audited: 2026-11-10 (Asia/Singapore).

## Per-invoice verdict

| Invoice | Verdict | Result pkg / GW | Amount (Net value / Goods value) | Lines / qty | Incoterms |
|---|---|---|---|---|---|
| AK00074096 | **pass** | 40 / 8,790.28 | 1,196,827 TWD | 24 / 7,024 | FOB Malaysia |
| AK00074097 | **pass** | 0 / 0 | 347,990 TWD | 8 / 257 | FCA Bosch Plant |
| AK00074098 | **pass** | 0 / 0 | 45,936 TWD | 1 / 528 | FCA Bosch Plant |

No field needs a gold override.

## 1. HU table (hand-counted from Marking page images)

Gross weights are **Gross HU Weight** from the Marking block, never Net HU Weight / Total Net Weight / line-level Gross Product Weight.

### AK00074096 — 30 unique HUs, 7,653.000 kg (matches printed Total Num of packages 30 / Total Gross Weight 7,653.000)

| # | HU (18-digit) | Gross HU Weight (kg) |
|---|----------------|----------------------|
| 1 | 406702140321238308 | 17.800 |
| 2 | 406702140321509101 | 100.000 |
| 3 | 406702140322158834 | 65.800 |
| 4 | 406702140322187506 | 96.000 |
| 5 | 406702140322187629 | 14.000 |
| 6 | 406702140322504815 | 400.000 |
| 7 | 406702140322505522 | 400.000 |
| 8 | 406702140322505942 | 400.000 |
| 9 | 406702140322506215 | 400.000 |
| 10 | 406702140322506901 | 400.000 |
| 11 | 406702140322518362 | 400.000 |
| 12 | 406702140322518461 | 320.000 |
| 13 | 406702140322520037 | 400.000 |
| 14 | 406702140322520112 | 400.000 |
| 15 | 406702140322520334 | 400.000 |
| 16 | 406702140322520419 | 400.000 |
| 17 | 406702140322520471 | 400.000 |
| 18 | 406702140322520556 | 400.000 |
| 19 | 406702140322520891 | 400.000 |
| 20 | 406702140322520921 | 400.000 |
| 21 | 406702140322521676 | 400.000 |
| 22 | 406702140322521690 | 400.000 |
| 23 | 406702140322521812 | 400.000 |
| 24 | 406702140322525421 | 3.600 |
| 25 | 406702140322527982 | 17.500 |
| 26 | 406702140322528200 | 3.400 |
| 27 | 406702140322528668 | 170.000 |
| 28 | 406702140322528804 | 25.800 |
| 29 | 406702140322529108 | 10.100 |
| 30 | 406702140322529986 | 9.000 |
| | **unique count / sum** | **30 / 7,653.000** |

Only the first row is labeled `RB`; later 18-digit ids without `RB` were still counted. POS-no / Net Val rows were not counted. Packing-material summary lines at the end (e.g. “17 Dummy Pack. Mat. for PALLET … Gross 6,800.000”) are type totals, not extra packages.

### AK00074097 and AK00074098 — the same 10 HUs, same weights

| # | HU (18-digit) | 097 Gross HU Weight | 098 Gross HU Weight |
|---|----------------|---------------------|---------------------|
| 1 | 406702140321949730 | 1.280 | 1.280 |
| 2 | 406702140322506154 | 310.000 | 310.000 |
| 3 | 406702140322528170 | 102.000 | 102.000 |
| 4 | 406702140323114235 | 400.000 | 400.000 |
| 5 | 406702140323149664 | 56.000 | 56.000 |
| 6 | 406702140323149916 | 56.000 | 56.000 |
| 7 | 406702140323150264 | 56.000 | 56.000 |
| 8 | 406702140323154286 | 56.000 | 56.000 |
| 9 | 406702140323179739 | 45.000 | 45.000 |
| 10 | 406702140323180025 | 55.000 | 55.000 |
| | **unique count / sum** | **10 / 1,137.280** | **10 / 1,137.280** |

Each file’s unique-HU sum equals its printed Total Num of packages / Total Gross Weight (10 / 1,137.280). No HU has a different weight across 097 vs 098. No rounding discrepancy (1.280 + 310 + 102 + 400 + 56×4 + 45 + 55 = 1,137.280 exactly).

### Overlaps and shipment union

- **096 ∩ (097 ∪ 098) = empty.** 096 does not share any HU with 097/098. (096’s ids are `…321238308`, `…321509101`, and `…32215…` / `…32218…` / `…32250…` / `…32251…` / `…32252…`; the shared 10 are `…321949730`, `…322506154`, `…322528170`, and six `…323…` ids.)
- 097 and 098 list **the same 10 HUs**. Adding the three printed totals (50 / 9,927.56) would double-count those 10.
- **Union (first wins):** 40 unique HUs, 7,653.000 + 1,137.280 = **8,790.280 kg**, reported as 8,790.28. Matches the Result on AK00074096.

## 2. Same shipment, lowest invoice number

All three invoices are the same shipment:

- Consignment Number **300037751** on every item block
- Billing Date **02.11.2026**, vendor Robert Bosch GmbH, same bill-to / ship-to, Shipping Point ADC MY outbound MALAYSIA, Shipping Mode Sea

Delivery numbers differ (096 = 800350767; 097 and 098 share 800355742) but that does not split the consignment.

Invoice numbers: AK00074096 < AK00074097 < AK00074098, so 096 is correctly the first invoice under shipment_first.

## 3. Headers and lines vs images

Checked invoice no., billing date, incoterms, Net value (this format’s Goods value; tax is 0 so Gross value equals Net value), line count, and every line’s PN / qty / amount / HS / origin against the rendered pages. All match the pack JSON. Line qty and amounts are the printed values; dedupe did not change them. Every commodity code is present.

**AK00074096** (24 lines, qty 7,024, Net value 1,196,827 TWD):

| Item | PN | Qty | Amount | HS | Origin |
|---|---|---:|---:|---|---|
| 10 | 1987.124.173-HUH | 6,528 | 789,888 | 3403999000 | MY |
| 20 | 1986.A01.400-WSK | 18 | 71,352 | 8511503200 | CN |
| 30 | 0986.580.415-KM9 | 7 | 15,757 | 8413303000 | PL |
| 40 | F026.400.482-KL9 | 40 | 12,480 | 8421312000 | DE |
| 50 | 1986.A00.882-CMT | 5 | 21,020 | 8511503200 | CN |
| 60 | 1986.A01.400-WSK | 9 | 35,676 | 8511503200 | CN |
| 70 | 0261.500.333-825 | 9 | 10,611 | 8409914900 | TR |
| 80 | 0258.986.79A-760 | 2 | 1,730 | 9027100000 | US |
| 90 | KS00.000.634-879 | 4 | 20,364 | 8413609000 | CN |
| 100 | 1986.AD4.001-879 | 5 | 3,970 | 8415901400 | CN |
| 110 | 1986.AD4.020-879 | 5 | 3,464 | 8415901400 | CN |
| 120 | 1986.AD4.000-879 | 5 | 3,069 | 8415901400 | CN |
| 130 | 1986.AD4.012-879 | 5 | 3,295 | 8415901400 | CN |
| 140 | 1986.AD4.021-879 | 3 | 2,479 | 8415901400 | CN |
| 150 | 1235.522.384-850 | 8 | 10,456 | 8511902000 | ES |
| 160 | 1986.S00.835-WGP | 3 | 7,884 | 8511403200 | CN |
| 170 | 1986.A01.033-YCL | 5 | 19,345 | 8511503200 | CN |
| 180 | 0580.464.121-FP5 | 31 | 43,493 | 8413303000 | CZ |
| 190 | 0241.145.529-7CF | 240 | 21,360 | 8511102000 | CN |
| 200 | 0221.503.035-8SL | 40 | 23,320 | 8511304900 | SI |
| 210 | 0258.027.005-001 | 24 | 28,800 | 9027100000 | DE |
| 220 | 0986.479.D61-WA9 | 16 | 9,536 | 8708309000 | CN |
| 230 | 1986.AD2.101-879 | 1 | 793 | 8415901400 | CN |
| 240 | 1986.A01.045-CMT | 11 | 36,685 | 8511503200 | CN |

**AK00074097** (8 lines, qty 257, Net value 347,990 TWD):

| Item | PN | Qty | Amount | HS | Origin |
|---|---|---:|---:|---|---|
| 10 | 0130.115.02R-879 | 5 | 7,275 | 8414593000 | CN |
| 20 | 0221.604.115-8SE | 103 | 42,539 | 8511304900 | SI |
| 30 | 0258.003.806-760 | 3 | 3,630 | 9027100000 | US |
| 40 | 0580.203.43T-FP5 | 125 | 221,375 | 8413303000 | CZ |
| 50 | 1986.A01.246-CMT | 5 | 26,275 | 8511503200 | CN |
| 60 | 1986.A01.519-ZRY | 7 | 23,569 | 8511503200 | CN |
| 70 | 1986.A01.246-CMT | 2 | 10,510 | 8511503200 | CN |
| 80 | F00E.263.207-750 | 7 | 12,817 | 9027100000 | JP |

**AK00074098** (1 line, qty 528, Net value 45,936 TWD): 1987.124.170-FXX, 528 PC × 87 = 45,936, HS 2710194600, origin MY.

## 4. Summary notes (printed pkg/GW)

The pack has JSON `summary_note` (no Result xlsx in this pack). Notes are correct:

- AK00074096: `shipment pkg/GW (deduped) 40 / 8790.28 on this first invoice (3 invoices, shared RB <the 10 HUs listed above>); printed pkg/GW 30 / 7653`
- AK00074097 and AK00074098: `shipment pkg/GW (deduped) on AK00074096; printed pkg/GW 10 / 1137.28`

Printed figures 30 / 7,653.000 and 10 / 1,137.280 are stored without trailing zeros, which is fine.

## 5. Bill of lading

No BL is in the review pack, `/workspace/ma_new_inv/`, or `/tmp/ma_ak7409/`. JSON BL fields are empty. Nothing to reconcile against the INV pkg/GW sum.

## 6. pytest and MA regression

- Full suite at `dce6c97` (worktree, `PYTHONPATH=/tmp/ie_dce6c97/src pytest -q`): **383 passed, 4 failed, 16 skipped**.
- The 4 failures are existing BHC 6th real-scan tests in `tests/test_bhc_6th.py` (`test_case8_original_3page_scan_end_to_end`, `test_jif_real_scan_gw_with_cell_reread` ×2, `test_case9_waybill_gw_needs_gold_when_cell_disagrees`). They call `extract_bl` on scan PDFs and got `(None, None, None)`. `tesseract` is not installed on this machine, so these are an environment limitation, not a regression from this MA branch. The same tests exist on `main`.
- MA-focused tests (`test_ma_ak_hu_dedupe.py`, `test_shared_rb_dedupe.py`, `test_ma_3rd.py`, `test_ma_3rd_round2.py`, `test_ma_hs_rb.py`, `test_ma_np_coo_index.py`): **77 passed, 1 skipped**.
- Independent text-layer regress of 251 MA invoices (179 `ma_no_period_v1`, 40 `ma_with_period_v1`, 32 `ma_ak_billing_v1`) across the usual MA batch roots: rerun at `dce6c97` **exactly matches** Invoice’s `after.json`. Versus pre-fix `before.json`, **only these three invoices change** (096 30/7653 → 40/8790.28; 097 and 098 10/1137.28 → 0/0 with notes). The other **248 MA invoices are unchanged**.

## Spot-check crops

1. `/workspace/ma_ak_74096_audit/crops/096_totals_30_7653.png` — printed 30 / 7,653.000 on 096.
2. `/workspace/ma_ak_74096_audit/crops/097_totals_10_1137.28.png` — printed 10 / 1,137.280 on 097 (098 is the same: `098_totals_10_1137.28.png`).
3. `/workspace/ma_ak_74096_audit/crops/097_marking_shared_hus_p3.png` — start of the 10 shared HUs on 097 (same list on `098_marking_first_hus.png` / `098_marking_remaining_hus.png`). 096’s disjoint first HUs: `096_marking_first_hus.png`. Consignment 300037751: `096_consignment_and_line1.png`.
