# Round2 — BHC / BITZER samples

Mega login expired; used `/home/box/Downloads/BHC_invoice_samples/` only (BITZER `3000214469_*.pdf`).

| status | PDF | invoice_no | amount | pkg | gw_kg | items | format | verdict | notes |
|--------|-----|------------|--------|-----|-------|-------|--------|---------|-------|
| PASS | 3000214469_TW_708822_BOSCH_HOME_COMFORT_TAIWAN_CO_LTD__Versa | 200167553 | 37041.41 | 7.0 | 6052.4 | 5 | bitzer_v1 | pass | ok |
| PASS | 3000214469_TW_708822_BOSCH_HOME_COMFORT_TAIWAN_CO_LTD__Versa | 200167553 | 37041.41 | 7.0 | 6052.4 | 5 | bitzer_v1 | pass | ok |

Expected BITZER header: invoice_no=200167553, amount=37041.41, pkg=7, gw=6052.4, lines=5.

JSON: `out/round2/*.json`

Auditor: `87eb5fb7-863d-4404-8489-9b16d6c8ef69`
