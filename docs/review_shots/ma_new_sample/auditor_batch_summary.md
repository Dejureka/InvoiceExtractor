# MA new sample (FormatSOP) — audit pack

**Date:** 2026-09-20 (Asia/Taipei)
**Root:** `/workspace/MA_batch_next/MAnewSample` — 10 folders, 19 INV + 5 BL/到貨/AWB
**Do not use:** archive / Mega wait

## Formats

| side | format_id | notes |
|------|-----------|-------|
| INV | `ma_ak_billing_v1` **(new family)** | Billing Document AK########; Commodity Code HS; Country of Origin per line; Marking HU pkg/GW |
| BL sea | `milestone_arrival_v1` | 90-S 到貨通知 HBL (694/712/713); 712 HBL005268 was scan → `.ocr.txt` sidecar |
| BL air | `nippon_express_awb_v1` **(new family)** | 50-N pdfdq NEM air waybill |

Existing `ma_no_period_v1` / `ma_with_period_v1` did **not** match (AK layout). Penalized Billing Document AK on NP/WP scorers.

## Pairing / hard results

| batch | invoice_nos | INV format | BL No. | BL pkg / GW | INV pkg / GW | hard |
|-------|-------------|------------|--------|-------------|--------------|------|
| 40-D-26MA-696 | AK00064692, AK00064693 | ma_ak_billing_v1 | — | — | 2 / 6.8 ; 1 / 21 | pass ×2 |
| 40-D-26MA-698 | AK00064959 | ma_ak_billing_v1 | — | — | 1 / 11.6 | pass ×1 |
| 40-D-26MA-701 | AK00065223, AK00065224 | ma_ak_billing_v1 | — | — | 1 / 10 ; 1 / 16 | pass ×2 |
| 40-D-26MA-735 | AK00067862 | ma_ak_billing_v1 | — | — | 1 / 0.5 | pass ×1 |
| 40-D-26MA-736 | AK00067883, AK00067884 | ma_ak_billing_v1 | — | — | 3 / 27.62 ; 1 / 4.6 | pass ×2 |
| 50-N-26MA-714 | AK00065676 | ma_ak_billing_v1 | NEM17159645 | 3 / 279 | 3 / 264.04 | pass ×1 |
| 50-N-26MA-733 | AK00067136 | ma_ak_billing_v1 | NEM17164630 | 1 / 68 | 1 / 68 | pass ×1 |
| 90-S-26MA-694 | AK00062356 | ma_ak_billing_v1 | HBL005250 | 4 / 3240 | 4 / 3240 | pass ×1 |
| 90-S-26MA-712 | AK00063832, AK00063833, AK00063834, AK00063839, AK00063843 | ma_ak_billing_v1 | HBL005268 | 58 / 9491.32 | 2 / 37.15 ; 5 / 966.2 ; 17 / 1680.5 ; 15 / 2763.27 ; 19 / 4026.77 | pass ×5 |
| 90-S-26MA-713 | AK00063846, AK00063847, AK00063848 | ma_ak_billing_v1 | HBL005267 | 11 / 3203.09 | 1 / 810 ; 5 / 2225 ; 5 / 168.09 | pass ×3 |

**Policy:** multi-INV same BL (712→5, 713→3) — each INV Summary row repeats shared BL No./pkg/GW; invoice Packages/G.W. untouched.

## Materials

- Pack: `docs/review_shots/ma_new_sample/` (JSON + PNG + `InvoiceExtract_Result.xlsx` + `BLExtract_Result.xlsx`)
- Auditor checklist: HBL/NEM nos, BL vs INV pkg/GW (712/713 sums ≈ BL), HS on every line, Marking HU packing.

Hard pass ≠ final accept.
