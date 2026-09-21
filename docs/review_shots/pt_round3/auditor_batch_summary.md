# PT round3 FormatSOP — auditor batch summary

**Date:** 2026-09-21 (Asia/Taipei)
**Root:** `/workspace/training_20260921/PT_new/` — 14 PDFs（忽略 .msg）
**Rules:** 既有 `pt_gloria_v1`（13）＋ `pt_dremel_head5_v1`（1）；**未**新增 PT format_id。

| invoice_no | format_id | hard | amt | pkg | GW | items | HS miss | notes | source |
|---|---|---|---|---|---|---|---|---|---|
| 50667175 | `pt_gloria_v1` | pass | 843.53 | None | 48.304 | 49 | 0 | pkg soft-missing; HS ok | `50-D-26PT-429_50667175.pdf` |
| 50666881 | `pt_gloria_v1` | pass | 3032.54 | 2.0 | 209.6 | 5 | 0 | HS ok | `50-D-26PT-434_50666881.pdf` |
| 50666882 | `pt_gloria_v1` | pass | 1301.5 | 1.0 | 99.3 | 4 | 0 | HS ok | `50-D-26PT-434_50666882.pdf` |
| 50667364 | `pt_gloria_v1` | pass | 46113.0 | None | 146.0 | 1 | 0 | pkg soft-missing; HS ok | `50-N-26PT-427_50667364.pdf` |
| 50667153 | `pt_gloria_v1` | pass | 101.7 | None | 21.5 | 5 | 0 | pkg soft-missing; HS ok | `50-N-26PT-428_50667153.pdf` |
| 50667783 | `pt_gloria_v1` | pass | 253.6 | None | 12.5 | 4 | 0 | pkg soft-missing; HS ok | `50-N-26PT-435_50667783.pdf` |
| 580021229 | `pt_dremel_head5_v1` | pass | 7810.56 | 1.0 | 266.0 | 1 | 0 | HS ok | `90-FLX-26PT-438_PPT.000699146300001.OUO1MTP.20260824-171341GMT.pdf` |
| 50659168 | `pt_gloria_v1` | pass | 71732.99 | 6.0 | 3349.29 | 287 | 0 | HS ok | `90-M-26PT-432_50659168.pdf` |
| 50667118 | `pt_gloria_v1` | pass | 14896.0 | 1.0 | 154.0 | 1 | 0 | HS ok | `90-S-26PT-426_TW_WT20260807000116_50667118_TW2026090701_BLUEWAY.pdf` |
| 50666907 | `pt_gloria_v1` | pass | 4341.6 | 3.0 | 260.72 | 4 | 0 | HS ok | `90-S-26PT-430_50666907.pdf` |
| 50667353 | `pt_gloria_v1` | pass | 3702.0 | 1.0 | 156.0 | 2 | 0 | HS ok | `90-S-26PT-431_50667353.pdf` |
| 50667440 | `pt_gloria_v1` | pass | 10484.95 | None | 154.0 | 1 | 0 | pkg soft-missing; HS ok | `90-S-26PT-433_50667440.pdf` |
| 50666217 | `pt_gloria_v1` | pass | 1737.84 | 2.0 | 50.4 | 2 | 0 | HS ok | `90-S-26PT-436_50666217.pdf` |
| 50666219 | `pt_gloria_v1` | pass | 23339.55 | 8.0 | 1158.453 | 19 | 0 | HS ok | `90-S-26PT-437_50666219.pdf` |

**Hard pass:** 14/14。規則未改。

## 材料
- Pack: `docs/review_shots/pt_round3/`（JSON + PNG p1–p2）
- 本批 hard 全過；截圖報告僅在 fail 時附失敗頁（本批無 fail）。
- Auditor 仍需對圖：金額＝Net invoiced／Value of Goods、GW＝Gross、每列 HS。

Hard pass ≠ final accept。
