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

**HS policy: hard** (same as MA / PT / SOE, not BHC soft), because the form has a per-line Commodity Code field like MA AK Billing. Three documents fail hard-check because the code is **not printed** — the parser did not invent one.

**shipment_first: not applied.** Every invoice prints `Total Num of packages 1` with a **different** Total Gross Weight (35–223 kg). Summing the 18 labelled totals = **18 packages / 2,446.000 kg**. There are no shared HU / packing keys. These look like per-invoice figures, not one shipment total repeated on every invoice.

## Please verify

1. **Classification / header** for each invoice: invoice no. AX00011132–AX00011149, date 2026-08-27, currency EUR not HUF, Incoterms FCA Miskolc, amount = labelled Net value EUR (equals Total value; tax is 0%).
2. **Lines:** PN, description, qty (EU thousands on 11135: 1.100 / 1.200 / 800), unit price, amount, Co, HS, N.W. LINE / QTY match. Pricing unit 100 PC must not be treated as if the unit price were per 1 PC.
3. **Packages / G.W.:** use each invoice’s own labelled totals (all pkg=1). Do **not** zero 17 invoices or put the 18 / 2,446 sum only on the first invoice unless you disagree with the reading above.
4. **AX00011144** is stamped **Copy** (the only Copy; there is no second file of this number). Content is still a full invoice (Battery EB12.100.076-VE4, 70 PC, 6.398,88 EUR, 1 / 195.000 kg).
5. **Missing Commodity Code (hard fail, please confirm it is really unprinted):**
   - AX00011144 and AX00011145: the single line `EB12.100.076-VE4` (Battery) has Country of Origin HU and Net Weight, but **no Commodity Code** at all.
   - AX00011148 item `EB13.900.025-VE4` (Service kit, 80 PC): Country of Origin HU, no Commodity Code. The other 12 lines on this invoice do print one.
6. **Anomalous line N.W. on AX00011148:** item `EB13.900.029-VE4` prints `Net Weight 8.292,000 KG` (extracted as 8,292 kg) while Total Net Weight is `33,097 KG` (= 33.097) and Total Gross Weight is `89,000 KG` (= 89.000). The extract **keeps the printed 8,292** and notes `line_nw_exceeds_total_nw`. If the intended value is 8,292 kg (8.292), that would be a document typography issue — please say what Result should show. Header G.W. still uses the labelled 89.000 kg.

Hard-check: 15 / 18 **pass**; the three invoices in (5) are **conflict** only because of missing HS. Amounts and line counts on those three still match the labels.

Please reply per invoice: pass / fix (with field and gold value). Also confirm the HS-hard policy and the no-shipment_first reading, and what to do with the 8.292,000 KG line.
