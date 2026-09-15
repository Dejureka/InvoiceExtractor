# MA INV＋提單 six packs — FormatSOP audit pack

**Date:** 2026-09-15 (Asia/Taipei)  
**Root:** `/home/box/Downloads/MA_inv_bl_6/` (6 folders, 15 PDFs)  
**Do not use:** `/home/box/Downloads/_archive_FormatSOP_DONE_勿重複訓練/`  
**Summary policy:** each INV row carries shared `BL No.` / `BL Packages` / `BL G.W. (kgs)` when multi-INV share one 到貨通知 (548, 616). Invoice Packages / G.W. never overwritten.

## Formats

| side | format_id | notes |
|------|-----------|-------|
| INV | `ma_no_period_v1` | All 90-S samples (no WithPeriod). HS on every line; Origin = Country Of Origin Index; RB packages/GW from INV packing. |
| BL | `milestone_arrival_v1` **(new family)** | 里運國際 / MILESTONE FORWARDING `ARRIVAL NOTICE 到貨通知書`. Tried CEVA/DHL/Hippopo first — layout is new; one family for all six HBLs (not one-per-file). |

## Pairing / hard results

| batch | invoice_nos | INV format | BL No. | BL pkg / GW | INV pkg / GW (per row) | hard |
|-------|-------------|------------|--------|-------------|------------------------|------|
| 90-S-26MA-524 | 2000269756 | ma_no_period_v1 | HBL005094 | 10 / 3765.6 | 10 / 3765.6 | pass |
| 90-S-26MA-548 | 2000270044, 2000270045 | ma_no_period_v1 | HBL005135 | 63 / 8337.15 | 3 / 72.1 ; 60 / 8265.05 (sum=BL) | pass ×2 |
| 90-S-26MA-589 | 2000270125 | ma_no_period_v1 | HBL005145 | 34 / 2821.03 | 34 / 2821.03 | pass |
| 90-S-26MA-616 | 2000270494, 2000270490, 2000270491 | ma_no_period_v1 | HBL005146 | 70 / 4902.362 | 45 / 3009.332 ; 4 / 199.77 ; 21 / 1693.26 (sum=BL) | pass ×3 |
| 90-S-26MA-621 | 2000271109 | ma_no_period_v1 | HBL005189 | 34 / 3669.19 | 34 / 3669.19 | pass |
| 90-S-26MA-623 | 2000271108 | ma_no_period_v1 | HBL005188 | 65 / 6611.52 | 65 / 6611.52 | pass |

**BL extract (all `milestone_arrival_v1`, hard pass):**

| HBL | vessel / voy | ETA | container | inv refs on BL |
|-----|--------------|-----|-----------|----------------|
| HBL005094 | WAN HAI 293 / N089 | 2026-07-03 | IAAU2759536 | 305229 (lubricants CI ≠ MA Document No.) |
| HBL005135 | WAN HAI 363 / N037 | 2026-07-14 | GCXU5353636 | 2000270044, 2000270045 |
| HBL005145 | WAN HAI 286 / N110 | 2026-07-24 | FYCU7167440 | 2000270125 |
| HBL005146 | WAN HAI 321 / N067 | 2026-08-01 | HPCU4760990 | 2000270490, 2000270491, 2000270494 |
| HBL005189 | INTERASIA VISION / N099 | 2026-08-02 | IAAU2752275 | 2000271109 |
| HBL005188 | INTERASIA VISION / N099 | 2026-08-02 | IAAU1985586 | 2000271108 |

## Materials

- JSON: `docs/review_shots/ma_inv_bl_6/*_INV_*.json`, `*_BL_*.json` (also `out/ma_inv_bl_6/json/batch_json/`)
- Excel Summary+BL: `InvoiceExtract_Result.xlsx`
- Excel BL sheet: `BLExtract_Result.xlsx`
- Shots: `*_BL_*-1.png`, `*_INV_*_p01*`, `*_p02*`, `*-rb*.png`

## Auditor checklist

1. Figure vs JSON: BL/HBL no, vessel/voyage, ETA, packages+unit, GW, container.
2. INV: Document No., Goods Value, line count, HS, Origin Index, RB packages/GW.
3. Summary: BL columns ≠ invoice Packages/G.W.; multi-INV rows (548/616) repeat same BL stats.
4. Hard pass ≠ final accept.

## CLI

```bash
python -m invoice_extractor /path/to/90-S-26MA-* --out InvoiceExtract_Result.xlsx
python -m invoice_extractor --doc-type bl 到貨通知\ HBL*.pdf --out BLExtract_Result.xlsx
```
