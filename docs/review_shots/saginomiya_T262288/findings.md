# Result validation

| Group | Name | Count |
| --- | --- | --- |
| invoices checked |  | 1 |
| status | hard | 0 |
| status | ok | 0 |
| status | warn | 29 |
| rule | W_GW_FROM_BL | 1 |
| rule | W_HS_MISSING | 28 |
| invoice | T262288 | 29 |

## Findings

| status | rule_id | invoice_no | row | field | expected | actual | page | position | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warn | W_GW_FROM_BL | T262288 | Summary!2 | gross_weight_kg | BL gross weight |  | 1 | (48.72, 113.71, 85.45, 124.27) | PL prints no gross-weight total (1,374.09 kg on the Total row is the Net Weight column) — invoice G.W. left blank; use BL G.W. |
| warn | W_HS_MISSING | T262288 | Lines!2 | hs_code | HS code |  | 1 | (212.2, 402.7, 259.48, 413.26) |  |
| warn | W_HS_MISSING | T262288 | Lines!3 | hs_code | HS code |  | 1 | (212.2, 402.7, 259.48, 413.26) |  |
| warn | W_HS_MISSING | T262288 | Lines!4 | hs_code | HS code |  | 1 | (212.2, 518.04, 259.48, 528.6) |  |
| warn | W_HS_MISSING | T262288 | Lines!5 | hs_code | HS code |  | 1 | (212.2, 568.92, 259.48, 579.48) |  |
| warn | W_HS_MISSING | T262288 | Lines!6 | hs_code | HS code |  | 1 | (212.2, 633.39, 259.48, 643.95) |  |
| warn | W_HS_MISSING | T262288 | Lines!7 | hs_code | HS code |  | 1 | (212.2, 697.83, 259.48, 708.39) |  |
| warn | W_HS_MISSING | T262288 | Lines!8 | hs_code | HS code |  | 1 | (212.2, 762.41, 259.48, 772.97) |  |
| warn | W_HS_MISSING | T262288 | Lines!9 | hs_code | HS code |  | 2 | (212.2, 196.27, 264.77, 206.83) |  |
| warn | W_HS_MISSING | T262288 | Lines!10 | hs_code | HS code |  | 2 | (212.2, 247.18, 259.48, 257.74) |  |
| warn | W_HS_MISSING | T262288 | Lines!11 | hs_code | HS code |  | 2 | (212.2, 311.62, 259.48, 322.18) |  |
| warn | W_HS_MISSING | T262288 | Lines!12 | hs_code | HS code |  | 2 | (212.2, 362.5, 259.48, 373.06) |  |
| warn | W_HS_MISSING | T262288 | Lines!13 | hs_code | HS code |  | 2 | (212.2, 413.28, 259.48, 423.84) |  |
| warn | W_HS_MISSING | T262288 | Lines!14 | hs_code | HS code |  | 2 | (212.2, 477.84, 259.48, 488.4) |  |
| warn | W_HS_MISSING | T262288 | Lines!15 | hs_code | HS code |  | 2 | (212.2, 542.28, 259.48, 552.84) |  |
| warn | W_HS_MISSING | T262288 | Lines!16 | hs_code | HS code |  | 2 | (212.2, 593.19, 259.48, 603.75) |  |
| warn | W_HS_MISSING | T262288 | Lines!17 | hs_code | HS code |  | 2 | (212.2, 593.19, 259.48, 603.75) |  |
| warn | W_HS_MISSING | T262288 | Lines!18 | hs_code | HS code |  | 2 | (212.2, 593.19, 259.48, 603.75) |  |
| warn | W_HS_MISSING | T262288 | Lines!19 | hs_code | HS code |  | 2 | (212.2, 698.43, 259.48, 708.99) |  |
| warn | W_HS_MISSING | T262288 | Lines!20 | hs_code | HS code |  | 2 | (212.2, 749.33, 259.48, 759.89) |  |
| warn | W_HS_MISSING | T262288 | Lines!21 | hs_code | HS code |  | 3 | (212.2, 182.59, 259.48, 193.15) |  |
| warn | W_HS_MISSING | T262288 | Lines!22 | hs_code | HS code |  | 3 | (212.2, 233.47, 259.48, 244.03) |  |
| warn | W_HS_MISSING | T262288 | Lines!23 | hs_code | HS code |  | 3 | (212.2, 284.38, 259.48, 294.94) |  |
| warn | W_HS_MISSING | T262288 | Lines!24 | hs_code | HS code |  | 3 | (212.2, 348.82, 259.48, 359.38) |  |
| warn | W_HS_MISSING | T262288 | Lines!25 | hs_code | HS code |  | 3 | (212.2, 413.28, 259.48, 423.84) |  |
| warn | W_HS_MISSING | T262288 | Lines!26 | hs_code | HS code |  | 3 | (212.2, 464.16, 259.48, 474.72) |  |
| warn | W_HS_MISSING | T262288 | Lines!27 | hs_code | HS code |  | 3 | (212.2, 528.6, 259.48, 539.16) |  |
| warn | W_HS_MISSING | T262288 | Lines!28 | hs_code | HS code |  | 3 | (212.2, 579.51, 259.48, 590.07) |  |
| warn | W_HS_MISSING | T262288 | Lines!29 | hs_code | HS code |  | 3 | (212.2, 630.39, 259.48, 640.95) |  |
