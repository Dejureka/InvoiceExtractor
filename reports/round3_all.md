# Round3 — all sample invoices (full pipeline)

**Date:** 2026-09-10 (Asia/Taipei)  
**Goal:** PT + BHC mega PDFs through classify → extract → hard_check; seed new formats; fix PT 50656831.

## Summary

| set | files | pass | conflict | needs_gold/ocr |
|-----|-------|------|----------|----------------|
| PT GmbH | 7 | 7 | 0 | 0 |
| BHC mega | 6 | 6 | 0 | 0 |
| **Total** | **13** | **13** | **0** | **0** |

## Fixes in this round

1. **PT 50656831:** removed global line-text dedupe (identical part/qty/amount lines are distinct deliveries); broadened material regex to `[A-Z0-9].ddd.xxx.xxx` (e.g. `F.016.800.581`). Raw match sum now equals Net invoiced value **114354.38** (374 lines).
2. **BITZER:** extract document-level `Country of origin: DE` + `HS-Code: 84143081` onto header and every item (Auditor note).
3. **New format seeds:** `hangji_v1` (GDHJ), `nidec_v1` (JCH VKT), `hitachi_gls_v1` (MEH), `highly_v1` (海立 26020900066).
4. **Packaging:** `vendor/pdf_layout_text` + `pyproject` `where = ["src","vendor"]`; portable Windows workflow + spec.

## PT GmbH

| status | PDF | invoice_no | amount | items | pkg | gw | currency | format | verdict | notes |
|--------|-----|------------|--------|-------|-----|----|----------|--------|---------|-------|
| PASS | 50656407.PDF | 50656407 | 10091.68 | 12 | 5.0 | 340.394 | USD | pt_gloria_v1 | pass | FCA Port Klang |
| PASS | 50656462.PDF | 50656462 | 10958.4 | 5 |  |  | USD | pt_gloria_v1 | pass | FCA CHENGDU |
| PASS | 50656463.PDF | 50656463 | 2506.32 | 1 |  | 162.288 | USD | pt_gloria_v1 | pass | FCA CHENGDU |
| PASS | 50656831.PDF | 50656831 | 114354.38 | 374 | 14.0 |  | USD | pt_gloria_v1 | pass | FCA Worms |
| PASS | 50656853.PDF | 50656853 | 87166.76 | 14 | 1.0 |  | USD | pt_gloria_v1 | pass | FCA Saame Plant |
| PASS | 50661052.PDF | 50661052 | 29587.2 | 1 | 1.0 |  | USD | pt_gloria_v1 | pass | FCA FACTORY |
| PASS | 50661078.PDF | 50661078 | 5221.44 | 2 |  | 324.576 | USD | pt_gloria_v1 | pass | FCA CHENGDU |

## BHC mega

| status | PDF | invoice_no | amount | items | pkg | gw | currency | format | verdict | notes |
|--------|-----|------------|--------|-------|-----|----|----------|--------|---------|-------|
| PASS | 3000214469_TW_708822_BOSCH_HOME_COMFORT_TAIWAN_CO_LTD__Versanddokument.pdf | 200167553 | 37041.41 | 5 | 7.0 | 6052.4 | EUR | bitzer_v1 | pass | origin=DE hs=84143081 FOB HAMBURG SEAPORT Free on board |
| PASS | GDHJ-250980(PI-2010-25055)  台湾博世 12-26.pdf | GDHJ-250980 | 797718.3 | 122 | 302.0 | 56689.0 | USD | hangji_v1 | pass | origin=CN FOB SHUNDE,CHINA |
| PASS | JCH-TW_VKT25097_Z2509281_LM.pdf | VKT25097 | 13062.96 | 3 | 6.0 | 2568.0 | USD | nidec_v1 | pass | origin=CN FOB SHANGHAI |
| PASS | JCH-TW_VKT25098_Z2509279-Z2509280.pdf | VKT25098 | 85846.13 | 5 | 29.0 | 13686.0 | USD | nidec_v1 | pass | origin=CN FOB SHANGHAI |
| PASS | SD(TW)_20260126_MEH6A036(TW99,TX68 etc).pdf | MEH6A036 | 631789.0 | 16 | 2.0 | 359.0 | JPY | hitachi_gls_v1 | pass | origin=JP F.O.B. SHIMIZU |
| PASS | 台湾博世 26020900066 DOCS.pdf | 26020900066 | 522785.34 | 7 | 271.0 | 113470.0 | USD | highly_v1 | pass | FOB SHANGHAI |

xls files skipped (v1 PDF-only).

JSON: `out/*.json` and `out/round3/*.json`.
