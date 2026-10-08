# BHC 6th batch — Auditor review pack (2026-10-08)

Source: `/home/box/Downloads/BHC-batch-6th/*.msg` (15 msg = 15 shipments), unpacked to
`BHC_6th data/case1…15` (Python sorted order of the .msg names); only the selected files in
`caseN/run/` were extracted. Branch `feature/bhc-6th` (from `main` @4fab308). No new format_id —
all changes extend existing ones (BHC: layout family `bhc_vendor_ci_v1` + vendor profiles).

Pack layout:
- `caseN__<file>/page_XXXX.png` — page images (100 dpi; Excel files rendered via LibreOffice, folder suffix `_xls`/`_xlsx`)
- `crops/` — key-field crops (invoice no., amount, PL GW, BL no., BL pkg/GW)
- `caseN_INV_<file>.json` — full extract per Result row (header, items, meta, `_hard` = hard-check), `caseN_BL_<file>.json` — BL extract
- `index.json` — files per case

| case | INV format_id (profile) | Invoice No. | Amount | LINE | QTY | pkg / GW (INV/PL) | Incoterm | BL format | BL No. / pkg / GW | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `bhc_vendor_ci_v1` (topband, NEW profile) | TB20260910 | USD 92,158.14 | 8 | 2,448 | 18 / 3,520 | FOB SHENZHEN | `hippopo_arrival_v1` | CPSE26090433 / 18 / 3,520 | pass |
| 2 | `bhc_vendor_ci_v1` (topband) | TB20261004 | USD 372,084.19 | 7 | 12,960 | 65 / 12,340 | FOB SHENZHEN | `hippopo_arrival_v1` | CPSE26100038 / 65 / 12,340 | pass |
| 3 | `dunan_v1` (PDF + xlsx twin, each with own PL twin) | DA15197958/47 | USD 59,597.42 | 2 | 6,140 | 35 / 4,676 | FOB SHENZHEN | `china_progress_bl_v1` | CPSE26090321 / 35 / 4,676 | pass |
| 4 | `bhc_my_hub_v1` | 9027850165 | USD 20,211.60 | 1 | 40 | 2 / 786 (rotated PL scan, OCR) | CIF Taipei | `ceva_pyramid_arrival_v1` | WEB260179386 / 2 / 786 | pass |
| 5 | `bhc_my_hub_v1` (PDF + xlsx twin) | 9027847785 | USD 146,317.23 | 5 | 71 | 71 / 17,652 (PDF row; xlsx row blank*) | CIF Taipei | `tvl_hbl_v1` | SHAKEL26971972 / 71 / 17,652 | pass |
| 6 | `hisense_qingdao_v1` (PDF + xlsx twin) | CIHT-TW-26090470 | USD 71,400.00 | 1 | 300 | 60 / 13,800 (PDF row; xlsx row blank*) | FOB | `tvl_hbl_v1` | QDEX2610001 / 60 / 13,800 | pass |
| 7 | `bhc_vendor_ci_v1` (hailiang, extended) | 26HLHK01Q4010 | USD 749,014.61 | 8 | 49,147 (KG) | 54 / 55,064 | FOB SHANGHAI | `tvl_hbl_v1` | SHAKEL26971215 / 54 / 55,064 | pass |
| 8 | `hitachi_gls_v1` (extended) | MEH6K018 | JPY 294,030 | 2 | 20 | 1 / 50 | F.O.B. SHIMIZU, JAPAN | `jif_cosmo_waybill_v1` (original 3-page scan; waybill picked by printed INVOICE NO.) | 261002KEE602 / 1 / 50 | pass (round 2) |
| 9 | `bhc_vendor_ci_v1` (hipus, extended; PDF + xlsx twin) | 117-BHCTW-26K-43 | JPY 3,397,361 | 24 | 8,969 | 6 / 1,774.5 (xlsx row; PDF row blank*) | FOB | `jif_cosmo_waybill_v1` | 261002KEE101 / 6 / 1,774.5 | pass |
| 10 | `bhc_vendor_ci_v1` (saginomiya, NEW) | T261565 | JPY 7,433,872 | 25 | 9,854 | 5 / **blank** + Summary note | FOB YOKOHAMA | `jif_cosmo_waybill_v1` (Ocean Links, extended) | KLG-T268Y98 / 5 / 1,460.9 | pass |
| 11 | `dunan_v1` (PDF + xlsx twin) | DA15199998/2/3/2/5 | USD 126,156.46 | 8 | 44,644 | 34 / 9,526 | FOB NINGBO | `china_progress_bl_v1` | NBSE26090062 / 34 / 9,526 | pass |
| 12 | `bhc_vendor_ci_v1` (augewei, NEW) | AGW202609300001 | USD 26,755.20 | 2 | 12,960 | 20 / 8,690.4 | FOB SHANGHAI | `tvl_hbl_v1` | **SHAKEL26C72175** / 20 / 8,690.4 | pass |
| 13 | `bhc_vendor_ci_v1` (jiangnan, NEW) | JCN26589 | USD 16,170.00 | 2 | 4,000 | 5 / 3,000 | FOB SHANGHAI | `tvl_hbl_v1` | **SHAKEL26C71898** / 5 / 3,000 | pass |
| 14 | `bhc_vendor_ci_v1` (wolong, NEW) | WLVN26501 | USD 45,113.58 | 3 | 2,058 | 12 / 5,045.56 | FOB HAIPHONG | `hippopo_arrival_v1` | P043ADNE2609 / 12 / 5,045.56 | pass |
| 15 | `bhc_vendor_ci_v1` (wolong) | WLA26322-3 | USD 8,652.00 | 2 | 480 | 4 / 1,841.6 | FOB | `hippopo_arrival_v1` | SHSE26090288 / 4 / 1,841.6 | pass |

`*` PDF + Excel twins of one invoice give two Result rows (as in all earlier batches). When the
shipment has only one PL, the PL pairs with one twin and the other twin's pkg/GW stays blank
(same as BHC 2nd case5/case8 and 4th case3). Invoice values of the twins are identical.

Selected / skipped files per case: see `BHC_6th data/selection.json` and `manifest.md`. Skipped:
HBL drafts when an arrival notice exists (cases 1, 2, 4, 14, 15), inline logos, case7 internal
明細.xls + three 装车单 loading slips, case10 `(材倉)T261565.pdf` (warehouse copy of the PL pages),
case11 产地证.pdf (COO). Duplicate BL copies collapsed (same BL no.): case6 `QDEX2610001.jpg`,
case9 scan `20261002225640-0001.pdf`.

## Needs a human read

None after Auditor round 2. Case 8 (formerly BL GW needs_gold) now runs the original 3-page scan
and outputs 261002KEE602 / 1 / 50. See `auditor_round2.md`.

## User decisions applied (2026-10-08)

- **Case 8**: only MEH6K018 + waybill 261002KEE602. Waybill 261002KEE601 (MEH6K019, 5 PLT / 745 kg)
  and its marks sheet (scan pages 1–2) were misplaced by the forwarder (missing invoice) and are not output.
  Round 2 runs the original 3-page PDF. The extractor selects KEE602 by its printed INVOICE NO. and names
  KEE601 as not used.
- **Case 14** (Wolong VN): words say "…Thirteen And Fifty Five Cents" but the numeric TOTAL is 45,113.58, which matches the sum of lines.
  The numeric total is used, with a note in `meta.notes`.
- **Case 15** (Wolong CN): the amount in words is garbled ("FOUR THOUSAND THREE HUNDRED AND TWENTY TWENTY
  SIX"). Numeric TOTAL 8,652.00 (= sum of lines) used + note.
- **Case 10** (Saginomiya): the PL prints no gross-weight total (the Total row 1,221.46 kg is the Net Weight column),
  so invoice G.W. is blank, with a soft `summary_note` (an Excel comment on the Summary G.W. cell). BL G.W. is 1,460.9.

## Soft notes

- Missing HS = soft (BHC): cases 1, 2, 4–12 print no HS on some/all lines. Case 13 HS = HTSUS
  8482990000 printed per line; case 14 HS 85013130 / case 15 8501310090 from the sheet header
  (applied to all lines).
- Origin not printed → blank + note: case 13 (Jiangnan), case 15 (Wolong CN). Case 5 line 5
  (RAM-10GS outdoor unit) has no COO on the invoice (PDF and xlsx) → blank. Case 10 origin per
  line (`(MADE IN CHINA)` → China, else Japan). Case 8 origins MY / CN.
- Case 13 incoterm printed `FOB EXPEDITORS SHANGHAI` (EXPEDITORS = forwarder) → FOB SHANGHAI + note.
  Case 15 incoterm printed `FOB` only (no named port) → `FOB` + note.
- Case 15: 3 zero-amount template rows skipped (note).
- Case 7: qty is KG (copper priced per KG); PN = PO NO (no Bosch PN printed); description kept
  as printed `REFINDED COPPER COIL`.
- Case 9 xlsx invoice twin has no TOTAL row (note: cross-check against the PDF; amounts equal).

## Hard-check notes

- All 15 cases: INV amount = labeled total = sum(lines); LINE/QTY consistent; unit price × qty
  per line within tolerance. No INV hard fail. All rows pass after round 2.
- INV/PL pkg/GW = BL pkg/GW on every case where both exist (case 10 INV GW blank by decision;
  case 8 = 1 / 50 on both sides after round 2).

## Rule changes for review

- `bhc_vendor_ci_v1`: NEW profiles topband / augewei / jiangnan / wolong / saginomiya;
  hailiang (`26HLHK01Q4010` number form, single-count PL TOTAL), hipus (PL units PALLET + CASE,
  TOTAL in PACKAGES/CASES). `Header.summary_note` passed through.
- `dunan_v1`: `parse_packing` hook (pkg from `TOTAL: N PALLETS/PACKAGES`; GW from the xlsx TOTAL
  row or the PDF sum row above TOTAL — case 11 generic parser took the first carton 2,764 →
  now 9,526 = BL); incoterm FOB SHENZHEN/SHANGHAI/… fallback.
- `bhc_my_hub_v1`: xlsx twin keeps the PDF column gaps in one cell (`RAM-18GSD   C          SF RAM,RAS`)
  → Excel input only: split PN / description at the widest gap (case 5 xlsx PN now `RAM-18GSD C` = PDF).
  hipus xlsx twin: country map adds Cambodia (case 9 lines 13–14, = PDF).
- `hitachi_gls_v1`: invoice no. on the line below `Invoice No.` (MEH6K018); inline-row description.
- `ocr.py`: pages with < 30% readable OCR tokens retry rotated 90/270 (psm 6/4), accepted only when
  ≥ 45% readable and better (case4 landscape PL scan). Generic factory-PL OCR TOTAL regex.
- Pairing: Chinese filename roles 发票 / 装箱单 (发票箱单 = combined); glued `PACKINGLIST-…` = PKL only
  when the name has no INVOICE; letter-spaced `I N V OI C E` title = invoice text; PDF↔PDF /
  Excel↔Excel tie-break for twins.
- BL: `tvl_hbl_v1` full `SHAKEL26C#####` numbers (case 12/13 were truncated / C read as 0),
  face package clip re-read under `No. of pkgs` (corroborates SAY/row reads or stands in when none
  — never outvotes SAY), loose face-GW locator; `jif_cosmo_waybill_v1` Ocean Links `KLG-…` waybill
  and `CONTAINER<6 PACKAGES>` / `N PALLETS & M CASES` (case 9 was 4 → 6); `hippopo_arrival_v1`
  sums `N PALLETS` when no PLTS; `china_progress_bl_v1` CPSE/SZSE numbers + `N PACKAGES / x KGS`.

## Regression (BHC 2nd / 3rd / 4th / 5th / mega samples, 32 folders)

Harness diff vs `main` @4fab308: **31/32 folders identical**. One change:
- BHC 3rd case 5 (Dunan FT00044266): Chinese filenames are now paired INV↔PL, giving 2 rows
  (PDF + xlsx) with pkg/GW 8 / 3,326 instead of 4 rows (two INV rows with blank pkg/GW plus the
  two PL files output as their own rows). The new output matches the **audited BHC 3rd gold**
  (`docs/review_shots/bhc_3rd/auditor_batch_summary.md`: DA15199998/2/5/52, 8 / 3326, "pkg from
  PKL"); the same vendor layout in this batch (cases 3/11) needs the pairing.
- Caught and fixed during regression (no remaining diff): BHC 5th case 3
  `TAWA-26024(260921)Invoice & Packinglist.pdf` (glued PACKINGLIST token made it PKL-only) and
  BHC 5th case 1 TVL BL pkg (face clip read 18 outvoted SAY SIX).
