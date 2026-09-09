# Round2 — BHC mega samples

Source: `/home/box/Downloads/BHC_invoice_samples_mega/` (Mega filled). xls skipped (v1 PDF-only).

| status | PDF | invoice_no | amount | items | format | verdict | chars | sniff | notes |
|--------|-----|------------|--------|-------|--------|---------|-------|-------|-------|
| PASS | 3000214469_TW_708822_BOSCH_HOME_COMFORT_TAIWAN_CO_LTD__Versanddokument.pdf | 200167553 | 37041.41 | 5 | bitzer_v1 | pass | 59471 | BITZER,Ladeliste,Invoice,Commercial,Packing | ok |
| NEEDS_GOLD | GDHJ-250980(PI-2010-25055)  台湾博世 12-26.pdf |  |  | 0 |  | needs_gold | 125168 | Invoice,Commercial,Packing,GDHJ | needs_ocr or needs_gold flagged |
| NEEDS_GOLD | JCH-TW_VKT25097_Z2509281_LM.pdf |  |  | 0 |  | needs_gold | 4912 | Invoice,Packing,JCH | needs_ocr or needs_gold flagged |
| NEEDS_GOLD | JCH-TW_VKT25098_Z2509279-Z2509280.pdf |  |  | 0 |  | needs_gold | 6140 | Invoice,Packing,JCH | needs_ocr or needs_gold flagged |
| NEEDS_GOLD | SD(TW)_20260126_MEH6A036(TW99,TX68 etc).pdf |  |  | 0 |  | needs_gold | 25169 | Invoice,Commercial,Packing,MEH | needs_ocr or needs_gold flagged |
| NEEDS_GOLD | 台湾博世 26020900066 DOCS.pdf |  |  | 0 |  | needs_gold | 5882 | Invoice,Packing | needs_ocr or needs_gold flagged |

**PDF count:** 6. **PASS/PASS*:** 1. Others = no seeded format yet → `needs_gold` (expected for v1; only `bitzer_v1` + `pt_gloria_v1` seeded).

BITZER expected: invoice_no=200167553, amount=37041.41, pkg=7, gw=6052.4, lines=5.

JSON: `out/round2/*.json`

Auditor bot: `87eb5fb7-863d-4404-8489-9b16d6c8ef69` — 未命中格式的供應商 PDF 可丟給 Auditor 做金標／規則提案。
