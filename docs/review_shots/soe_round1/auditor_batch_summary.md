# SOE round1 FormatSOP — auditor batch summary

**Date:** 2026-09-21 (Asia/Taipei)
**Root:** `/workspace/training_20260921/SOE_1st/` — 8 folders, 13 INV + 2 HAWB（忽略 .msg）

## Formats（new）

| side | format_id | anchors |
|------|-----------|---------|
| INV | `soe_rb_gmbh_v1` **(new)** | `Robert Bosch GmbH`、`Bosch Partnumber`、`Invoice Copy`／`Invoice and Packing List`、`Invoice amount`、`Total gross weight`、`Customs tariff no`；inv 70775…／70918… |
| BL air | `kwe_air_waybill_v1` **(new)** | Kintetsu World Express HAWC `1220-########` |
| BL air | `maersk_air_waybill_v1` **(new)** | Maersk Logistics HAWB `QU########` |

BHC `INV_PL_*` 弱分已罰掉（不再誤認 `bhc_my_hub_v1`）。MA NP/WP 亦對 Bosch Partnumber 扣分。

## INV hard results

| folder | invoice_no | hard | amt EUR | pkg | GW | items | backend | file |
|--------|------------|------|---------|-----|----|-------|---------|------|
| 50-D-26SOE-170 | 7091802382 | pass | 160254.62 | 12.0 | 341.0 | 1 | ocr/tesseract | `1267620500 taiwan.pdf` |
| 50-KWE-26SOE-179 | 7077539868 | pass | 27875.35 | 1.0 | 497.0 | 1 | pdftotext -layout | `INV_PL_7077539868.pdf` |
| 50-KWE-26SOE-182 | 7077559620 | pass | 27875.35 | 1.0 | 496.0 | 1 | pdftotext -layout | `INV_PL_7077559620.pdf` |
| 50-M-26SOE-175 | 7077540510 | pass | 80934.57 | 2.0 | 294.5 | 1 | pdftotext -layout | `7077540510.PDF` |
| 50-N-26SOE-174 | 7077533916 | pass | 159.98 | 1.0 | 26.628 | 1 | pdftotext -layout | `7077533916.pdf` |
| 90-S-26SOE-178 | 7077533772 | pass | 39239.42 | 2.0 | 491.416 | 1 | pdftotext -layout | `7077533772.pdf` |
| 90-S-26SOE-178 | 7077533915 | pass | 24951.36 | 1.0 | 334.172 | 1 | pdftotext -layout | `7077533915.pdf` |
| 90-S-26SOE-178 | 7077533945 | pass | 24951.36 | 1.0 | 334.172 | 1 | pdftotext -layout | `7077533945.pdf` |
| 90-S-26SOE-180 | 7077530220 | pass | 68089.44 | 1.0 | 108.0 | 1 | pdftotext -layout | `7077530220 WJC20260824050.pdf` |
| 90-S-26SOE-180 | 7077530221 | pass | 2855.9 | 2.0 | 65.5 | 2 | pdftotext -layout | `7077530221 WJC20260824052.pdf` |
| 90-S-26SOE-180 | 7077530222 | pass | 4230.58 | 1.0 | 38.5 | 1 | pdftotext -layout | `7077530222.PDF` |
| 90-S-26SOE-181 | 7077535921 | pass | 102384.96 | 4.0 | 1336.688 | 1 | pdftotext -layout | `7077535921.pdf` |
| 90-S-26SOE-181 | 7077535952 | pass | 26517.17 | 1.0 | 303.288 | 1 | pdftotext -layout | `7077535952.pdf` |

**Hard pass INV:** 13/13

## BL / HAWB

| folder | format_id | BL No. | pkg | GW | inv_ref | hard | file |
|--------|-----------|--------|-----|----|---------|------|------|
| 50-KWE-26SOE-182 | `kwe_air_waybill_v1` | 1220-19555195 | 1.0 | 496.0 | 7077559620 | pass | `122019555195-HAWC.pdf` |
| 50-M-26SOE-175 | `maersk_air_waybill_v1` | QU100002136 | 2.0 | 294.5 | 7086963306 | pass | `Copy 7 - (Extra Copy) - HAWB No_ QU100002136.pdf` |

**Hard pass BL:** 2/2

## Notes for Auditor
- GW＝**Total gross weight**（非 Net）；pkg＝Marking summary `N Pallets`（OCR 1267620500 用 cargo `12 Pallets`）。
- 金額＝標籤 **Invoice amount**；Price unit 100 → unit_price=Price/100。
- HS hard：每列 Customs tariff no（含 OCR 7091802382）。
- 配對：50-KWE-182 INV 7077559620 ↔ HAWB 1220-19555195；50-M-175 INV 7077540510 ↔ HAWB QU100002136（面額 Invoice No. 可能不同單號，Auditor 核對）。
- 截圖：本批 hard 全過，無 fail-only 圖集；JSON＋首頁 PNG 在 pack 供對圖。

## Materials
- Pack: `docs/review_shots/soe_round1/`

Hard pass ≠ final accept。
