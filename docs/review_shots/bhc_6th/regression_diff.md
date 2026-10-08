# BHC 6th — regression diff vs main @4fab308 (harness, 32 folders: BHC 2nd/3rd/4th/5th + mega)

Only change: BHC 3rd case 5 — INV↔PL now paired via Chinese filenames (8 / 3326 on the INV rows = audited BHC 3rd gold); PL files no longer output as their own rows.

```
== /home/box/Downloads/BHC-batch-0924/3rd data/case 5
  row ('标准_结汇发票FT00044266.pdf', '—', '44266提单.pdf') only in main DA15199998/2/5/52 None None NBSE26090042 8.0 3326.0
  row ('标准_结汇发票FT00044266.pdf', '标准_结汇装箱单FT00044266.pdf', '44266提单.pdf') only in feat DA15199998/2/5/52 8.0 3326.0 NBSE26090042 8.0 3326.0
  row ('标准_结汇发票FT00044266.xlsx', '—', '44266提单.pdf') only in main DA15199998/2/5/52 None None NBSE26090042 8.0 3326.0
  row ('标准_结汇发票FT00044266.xlsx', '标准_结汇装箱单FT00044266.xlsx', '44266提单.pdf') only in feat DA15199998/2/5/52 8.0 3326.0 NBSE26090042 8.0 3326.0
  row ('标准_结汇装箱单FT00044266.pdf', '—', '44266提单.pdf') only in main DA15199998/2/5/52 8.0 3326.0 NBSE26090042 8.0 3326.0
  row ('标准_结汇装箱单FT00044266.xlsx', '—', '44266提单.pdf') only in main DA15199998/2/5/52 8.0 None NBSE26090042 8.0 3326.0
folders differing: 1 of 32
```

## Round 2 (2026-10-08, after Auditor review @ecf69bb)

- BHC 2nd–5th + mega (32 folders) vs `main` @4fab308: only BHC 3rd case 5 differs (unchanged from round 1). Old JIF
  waybills (4th case 6, case 8 + scan copy) are identical.
- BHC 6th vs ecf69bb review-pack JSONs: only case 8 changed (BL file = original 3-page scan; BL G.W. blank → 50;
  needs_gold → pass). The other 14 cases have identical Result fields.
