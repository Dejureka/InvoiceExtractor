# BHC 4th batch — Auditor review pack (2026-10-05)

Source: `/home/box/Downloads/BHC-batch-4th/BHC_4th data/case 1…11` (MEGA `/BHCsamples/BHC_4th data.zip`). All `.msg` ignored.
Branch `feature/bhc-4th` (based on `feature/auto-open-result`). Per-case JSON = `case*_*.json` in this folder.
Screenshots only for parts that need a human read (BL OCR disagreements / blank cells).

| case | files (non-.msg) | INV format_id | Invoice No. | Amount | LINE | pkg / GW (INV/PL) | Incoterm | BL file → format | BL No. / pkg / GW | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `SHC-THT2609029客户资料.pdf` (INV+PL) + `.xls` twin; BL scan `20260921141756-0001.pdf` | `bhc_vendor_ci_v1` (sanhua) NEW | SHC/THT2609029 | USD 27,623.74 | 6 | 8 / 3185 | FOB SHANGHAI | TVL HBL → `tvl_hbl_v1` | SHAKEL26971822* / 8 / 3488* | **needs_gold** (bl_no, bl_gw) |
| 2 | `SATJG26011.pdf` (OCR); BL scan `20260923094309-0001.pdf` | `suzhou_aichi_v1` (extended) | SATJG26011 | 66,150.64 | 2 | 12 / 7574 | FOB SHANGHAI | `tvl_hbl_v1` | SHAKEL26971920 / 12 / 7574 | pass |
| 3 | `INV+PL+CIHT-TW-26090405.pdf` + `.xlsx` twin; BL photo `QDEX2609096.jpg` | `hisense_qingdao_v1` | CIHT-TW-26090405 | 33,565 | 3 | 30 / 4500 | FOB | `tvl_hbl_v1` (image OCR, NEW input type) | QDEX2609096 / 30 / 4500 | pass |
| 4 | `(JCH26-09M2) Invoice, PL.pdf`; `Bill Of Lading - NGOA24053.pdf` | `marubeni_tetsugen_v1` | JCH26-09M2 | 59,144.08 | 2 | 5 / 2993 | FOB NAGOYA, JAPAN | `dhl_danmar_bl_v1` | NGOA24053 / 5 / 2993 | pass |
| 5 | `26HLHK01Q10009B-发票箱单.xlsx` (INV+PL); BL scan `20260922194949-0001.pdf` | `bhc_vendor_ci_v1` (hailiang) NEW | 26HLHK01Q10009B | 770,025.90 | 1 | 54 / 54288 | FOB SHANGHAI | `tvl_hbl_v1` | SHAKEL26971161 / 54 / 54288 | pass (2 soft notes) |
| 6 | `20260923_MEH6J044(…).pdf`; empty template `SSLJP0023526  MEH6J044.xls` (skipped); `BL.pdf` | `hitachi_gls_v1` (extended) | MEH6J044 | JPY 18,143,405 | 7 | 16 / 1998 | F.O.B. SHIMIZU, JAPAN | `jif_cosmo_waybill_v1` NEW | 260918KEE103 / 16* / —* | **needs_gold** (bl_pkg, bl_gw) |
| 7 | `BHCWHJTV2609004_INV_9027784701.PDF` + `PKL_…pdf`; `SHAKEL26971969.pdf` | `bhc_my_hub_v1` | 9027784701 | 177,725.70 | 3 | 90 / 21870 | CIF Taipei | `tvl_hbl_v1` | SHAKEL26971969 / 90 / 21870 | pass |
| 8 | `IV_117-BHCTW-26K-41.PDF`+`.xlsx`, `IV_121-BHCTW-26K-37.PDF`+`.xlsx`, shared `PL_117…, 121….xlsx`; `WAYBILL.pdf` + scan copy `20260921195744-0001.pdf` | `bhc_vendor_ci_v1` (hipus) NEW | 117-BHCTW-26K-41 / 121-BHCTW-26K-37 | JPY 10,014,860 / 15,300 | 43 / 1 | 117: 10 / 3084.5; 121: 0 / 0 (shared PL rule) | FOB | `jif_cosmo_waybill_v1` NEW | 260918KEE102 / 10* / 3084.5* | **needs_gold** (bl_pkg, bl_gw) |
| 9 | `BHC-TW_VKT26073_Z2609284.pdf`; BL scan `20260924135224-0001.pdf` | `nidec_v1` | VKT26073 | 129,780 | 4 | 44 / 20257 | FOB SHANGHAI | `tvl_hbl_v1` | SHAKEL26971860 / 44 / 20257 | pass |
| 10 | `CI PL MDBWHTWJCH260915.pdf` (INV+PL); `到貨通知.pdf` | `bhc_vendor_ci_v1` (welling) NEW | MDBWHTWJCH260915 | 126,756 | 3 | 63 / 28972.8 | FOB BEIJIAO | `hippopo_arrival_v1` | CPSE26090124 / 63 / 28972.8 | pass (Co blank) |
| 11 | `COMMERCIAL_INVOICE BHC-TW 2026-09-23.xls` + `PACKING LIST … .xls`; `到貨通知.pdf` | `bhc_vendor_ci_v1` (broad_ocean) NEW | 2026-09-23-BHC-TW | 13,641.60 | 1 | 7 / 1876 | FOB ZhongShan | `hippopo_arrival_v1` | CPSE26100002 / 7 / 1876 | pass |

`*` = needs_gold field (suggested value shown; see shots). Twins (PDF + Excel of the same invoice) give two Result rows as in earlier batches; their values are identical (case 8 lines compared 1:1).

## Needs a human read (with screenshots)

1. **Case 1 BL (TVL scan)** — OCR 200 dpi read `SHAKEL26871822` / `3488.000 KGS`; 300 dpi read `SHAKEL26971822` / no GW. Image (`case1_bl_no_SHAKEL26971822.png`, `case1_bl_face_pkg_gw.png`) shows **SHAKEL26971822, 8 PALLETS, 3185.000 KGS** (= INV/PL 3185). Tool keeps BL No. SHAKEL26971822 (higher-dpi read), GW 3488 as suggested value → flagged `bl_no`, `bl_gross_weight_kg`. Gold: SHAKEL26971822 / 8 / 3185.
2. **Case 6 BL (JIFFA / Cosmo waybill 260918KEE103)** — anti-counterfeit background; OCR gets no pallet count and only `998, 000` for GW. Pkg 16 is from the attached sheet's last `CASE NO. 16`. Image (`case6_jif_waybill_pkg_gw.png`) shows **16 PALLETS (4,815 PIECES), 1,998.000 KGS** (= INV 16 / 1998). Gold: 260918KEE103 / 16 / 1998.
3. **Case 8 BL (waybill 260918KEE102)** — `WAYBILL.pdf` gives `CONTAINER<10 PALLETS` and `3,084,500` (one read each); scan copy unreadable. Image (`case8_jif_waybill_pkg_gw.png`, `case8_jif_waybill_scan_copy_pkg_gw.png`) shows **10 PALLETS (31,670 PIECES), 3,084.500 KGS** (= PL 10 / 3084.5). Gold: 260918KEE102 / 10 / 3084.5. Scan copy is the same BL no → not used (note on row).
4. **Case 1 Sanhua PDF row P10062198-30** — CUSTOMERS NO. cell is blank on the PDF (`case1_sanhua_pdf_blank_customer_no.png`); the `.xls` twin has `3HH37914N`. PDF row PN = blank + note; xls row PN = 3HH37914N.

## Soft notes / user decisions

- **Case 8 shared PL (one PL for invoices 117 + 121)** — extended the MA 2026-09-29 rule (`shipment_first`): 10 / 3084.5 on 117 (both PDF and xlsx rows), 0 / 0 on 121 + Summary note. **Needs user OK that the MA rule applies to BHC too.**
- **Case 5 Hailiang** — PL also prints `INVOICE NO.: 10HLHK01A0313` (looks like template residue; invoice sheet / PL header / filename all say 26HLHK01Q10009B). PL TOTAL row has two counts 22 and 54; tool uses 54 (PACKAGES column) = BL 10+22+22 = 54. PN = PO NO `P100592670060` (no Bosch PN printed; copper priced per KG).
- **Case 10 Welling** — origin not printed → Co blank (note).
- **Case 6** `SSLJP0023526  MEH6J044.xls` is an empty form (labels only) → skipped (`SKIP … empty Excel template`).
- Missing HS: soft for BHC (cases 3, 4, 6, 7, 8, 9, 10, 11 print no HS on some/all lines).

## Hard-check notes

- All 11 cases: INV amount = labeled total = sum(lines); LINE/QTY consistent. No INV hard fail.
- Before the fixes, case 2 was a **fake pass** (1 line, GW = Net 7277, FOB SHENZHEN) and case 6 passed with 0 lines; both fixed (labeled totals; 0 lines → needs_gold).
- TVL BLs: previously cases 2 / 5 / 7 BL pkg were wrong (1 = container count, 30 = one container); now voted from SAY TOTAL / container-row sums that must add up to the face GW.

## Rule changes for review

- NEW `bhc_vendor_ci_v1` (one layout family, profiles sanhua / welling / broad_ocean / hipus / hailiang; `parse_packing` hook for split PKL).
- NEW BL `jif_cosmo_waybill_v1` (≥2 agreeing OCR reads, else needs_gold — same policy as `kwe_sea_waybill_v1`).
- `tvl_hbl_v1`: second OCR pass (300 dpi) on scans + vote; BL-no disagreement → needs_gold (GW too if only one read); QDEX B/L no.
- `suzhou_aichi_v1`, `hitachi_gls_v1` extended (old samples unchanged: BHC 3rd case1 40875 / 7 / 4121; MEH6A036 16 lines 2 / 359).
- Pairing: `CI` token; one PKL named after ≥2 INVs → attached to all; duplicate BL copies (same BL no) collapse to the best copy; empty Excel templates skipped; vendor-aware PKL parser.
- Image input (.jpg/.jpeg/.tif; .png as explicit file only).
- Regression (BHC 2nd / 3rd / mega samples): only two changes — BHC 2nd case1 `QDEX2609010.jpg` is now read (BL No. QDEX2609010, GW 45986 from one OCR read (= INV), BL pkg needs_gold: the container table and SAY TOTAL words are not readable); mega `DF_SFA006358 MEH6A036 IV PL.xls` (empty form) is now skipped instead of an empty needs_gold row.
