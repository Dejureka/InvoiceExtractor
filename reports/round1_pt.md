# Round1 — PT GmbH samples

Trained/verified against `pdftotext -layout` from `/workspace/msg_extract/**/*.PDF`.

| status | PDF | invoice_no | amount | items | currency | format | verdict | notes |
|--------|-----|------------|--------|-------|----------|--------|---------|-------|
| PASS | 50656407.PDF | 50656407 | 10091.68 | 12 | USD | pt_gloria_v1 | pass | ok |
| PASS | 50656462.PDF | 50656462 | 10958.4 | 5 | USD | pt_gloria_v1 | pass | ok |
| PASS | 50656463.PDF | 50656463 | 2506.32 | 1 | USD | pt_gloria_v1 | pass | ok |
| PASS* | 50656831.PDF | 50656831 | 114354.38 | 330 | USD | pt_gloria_v1 | conflict | sum(item.amount) 110966.20999999999 != header.amount 114354.38 |
| PASS | 50656853.PDF | 50656853 | 87166.76 | 14 | USD | pt_gloria_v1 | pass | ok |
| PASS | 50661052.PDF | 50661052 | 29587.2 | 1 | USD | pt_gloria_v1 | pass | ok |
| PASS | 50661078.PDF | 50661078 | 5221.44 | 2 | USD | pt_gloria_v1 | pass | ok |

**Summary:** 7/7 extracted invoice_no. PASS* = invoice_no ok but hard-check conflict.

JSON: `out/round1/*.json`

Auditor bot id=`87eb5fb7-863d-4404-8489-9b16d6c8ef69` — 對帳可丟給 Auditor。
