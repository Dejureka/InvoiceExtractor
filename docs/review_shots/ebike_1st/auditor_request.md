# Auditor request — eBike 1st (Bosch Energy and Body Systems Kft, AX Billing)

**Scope:** 18 commercial invoices, first batch of a **new business unit** (eBike). Issuer is Robert Bosch Energy and Body Systems Kft, Miskolc, Hungary. All are text-layer PDFs (Adobe LiveCycle), not scans. No packing-list files and no BL in this upload. All 18 share consignment `0050142328`, billed 27.08.2026, Incoterms `FCA Miskolc`, currency **EUR** (a statutory HUF conversion is also printed — do not use HUF).

**Branch:** `feature/ebike-1st` (not pushed / not merged).

**Pack:** this folder.
- `INV_AX000111xx.json`: extract + `_hard` hard-check. `_stamp` is Original vs Copy. `_consignment` is the shared consignment number.
- `pages/`: every invoice page at 120 dpi.
- `crops/`: header (Billing Document), EUR totals + Incoterms, labelled packages / G.W., plus the missing-HS and anomalous line-NW spots below.

## Format decision

The SAP “Billing Document / Bosch Material No. / Commodity Code” *form* is a cousin of `ma_ak_billing_v1`, but this is **not** an extension of that format_id:

- Invoice numbers are **AX########**, not AK.
- Numbers are **EU** (`18.022,42`, qty `1.100` = 1100), not US.
- Amount is labelled `Net value … EUR` (ignore the HUF block).
- Packages / G.W. are the printed `Total Num of packages` / `Total Gross Weight` (no Marking HU block).
- Unit prices are per **Pricing Unit** (100 PC on this batch). Line amount = qty × unit price / pricing unit, which matches the printed Net Value.

New format_id: **`ebike_ax_billing_v1`**. `ma_ak_billing_v1` now loses score on AX / “Energy and Body Systems” so it does not steal these files (the current portable on main mis-classifies all 18 as MA AK and extracts almost nothing).

## User rules (2026-11-10) — already applied

1. **HS policy for `ebike_ax_billing_v1` only: soft.** If Commodity Code is not printed, leave HS empty and record a soft warning on `meta.notes` and `header.summary_note` (Excel comment on the Summary Packages / G.W. cells). Do **not** invent a code. Hard-check stays **pass**. MA / PT / SOE HS rules are unchanged (still hard).
2. **No shipment_first.** Each invoice keeps its own printed pkg / G.W. (all pkg=1, distinct GW 35–223 kg; sum 18 / 2,446.000 kg). Do not zero 17 invoices or move the sum onto the first invoice.
3. **AX00011148 line `EB13.900.029-VE4` N.W.:** keep the printed `8.292,000 KG` as **8,292 kg**, with note `line_nw_exceeds_total_nw` on Summary (Total Net Weight is `33,097 KG` = 33.097; Total Gross Weight is `89,000 KG` = 89.000). Header G.W. still uses the labelled 89.000 kg.
4. **AX00011144 Copy** is a real invoice (the only Copy; no Original twin).

## Please verify

1. **Classification / header** for each invoice: invoice no. AX00011132–AX00011149, date 2026-08-27, currency EUR not HUF, Incoterms FCA Miskolc, amount = labelled Net value EUR (equals Total value; tax is 0%).
2. **Lines:** PN, description, qty (EU thousands on 11135: 1.100 / 1.200 / 800), unit price, amount, Co, HS, N.W. LINE / QTY match. Pricing unit 100 PC must not be treated as if the unit price were per 1 PC.
3. **Packages / G.W.:** each invoice’s own labelled totals (all pkg=1), per user rule 2.
4. **AX00011144** is stamped **Copy** but extracted as a full invoice (Battery EB12.100.076-VE4, 70 PC, 6.398,88 EUR, 1 / 195.000 kg), per user rule 4.
5. **Missing Commodity Code (soft, HS left empty — please confirm it is really unprinted):**
   - AX00011144 and AX00011145: the single line `EB12.100.076-VE4` (Battery) has Country of Origin HU and Net Weight, but **no Commodity Code**.
   - AX00011148 item `EB13.900.025-VE4` (Service kit, 80 PC): Country of Origin HU, no Commodity Code. The other 12 lines on this invoice do print one.
   These three are hard-check **pass** with a Summary note `soft: Commodity Code not printed on …; HS left empty`.
6. **Anomalous line N.W. on AX00011148:** item `EB13.900.029-VE4` prints `Net Weight 8.292,000 KG` (8,292 kg) vs Total Net Weight 33.097 kg / GW 89.000 kg, per user rule 3. The Summary note also carries `line_nw_exceeds_total_nw`.

Hard-check: **18 / 18 pass** (the three invoices in (5) pass with a soft HS warning; amounts and line counts still match the labels).

Please reply per invoice: pass / fix (with field and gold value).
