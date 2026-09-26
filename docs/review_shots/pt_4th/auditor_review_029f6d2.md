# PT 4th batch — Auditor review (independent, read-only)

**Date:** 2026-09-26 (Asia/Taipei, box clock) · **Branch/commit audited:** `feature/pt-4th` @ `029f6d2` (no code/rules/branch changes made) · **Inputs:** `/home/box/Downloads/PT-batch-4th/4th data/` (23 PDFs) · **JSONs:** `docs/review_shots/pt_4th/<stem>.json` (= `_auditor_payload_all23.json`)

Scratch work (independent parser, renders, OCR, historical-snapshot outputs): `/workspace/pt4audit/` (outside the repo).

## Verdict summary

- **pass 22 · conflict 0 · needs_gold 1** (`50663231` — total_pkg).
- Tools report says 23/23 pass with no needs_gold → **I do not accept 50663231 as pass**; see soft item 1.
- Hard check re-run (`PYTHONPATH=src`, `checker.hard_check`) on all 23 JSONs: 23/23 `pass`, issues `[]` (matches meta.checker_verdict). Note: `meta.labeled_amount` is null in all 23, so the hard check only proves header.amount = sum(lines); the labeled-total comparison below was done independently.

## Method

1. `pdftotext -layout` regenerated from the source PDFs (not reusing Tools' `out/pt_4th/txt`). All 23 have a real text layer (embedded fonts; 4–43 pages).
2. Independent regex parser written for this audit (`/workspace/pt4audit/indep.py`): every material row (`<mat.no.> … <qty> <unit> <price> <amount>` + next-line `CC HSCODE`), `Net invoiced value of goods`, `Total … **`, incoterm line under Total, `Value:`, `Gross Weight:`, Packing-details rows / `Shipping unit <ID>` / type summary / `total : N`, tariff-code block, country-of-origin block.
3. JSON vs PDF compared field-by-field (`compare.py`): invoice_no, date, currency, amount vs NIV vs `Total` vs `Value:`, incoterm, GW vs `Gross Weight:` vs packing footer vs sum of packing-row gross, pkg vs unique Shipping-unit IDs (or unique packing rows when no SU), line count, total qty, and per line part_no/qty/unit/price/amount/origin/HS. Plus per-HS line sums vs the printed tariff block, and line origins vs the COO block.
4. Visual check: rendered (pdftoppm) and viewed all pages of the 3 new files that carry data (50664923 p2/p4; 50654373 p1–4; 50654372 p34/p37/p38/p43 + row crops), and the soft-item pages (50663231 p4; 50664217 p2/p3/p4 + 300-dpi crop; 50665615 p1/p3 + 300-dpi crop).
5. OCR cross-check (Tesseract, 250–300 dpi) of **every page of all 23 PDFs**: for every JSON line the printed `origin HS`, line amount and part no., and header invoice no./amount/GW/incoterm were searched in the OCR text. All 429×(HS+amount) and all header values found; 4 part-no. OCR misses (0↔O confusions: 1.600.A03.AK0, 2.608.901.952 in 50654372; 0.601.081.3K0 ×2 in 50664379) were checked on 250-dpi crops and match the JSON.
6. Byte identity: sha256 of each batch PDF vs `~/Downloads/_archive_FormatSOP_DONE_勿重複訓練/PTsamples_Gloria_20pdfs/`.
7. Regression: the Round4 JSONs are not all on disk (`out/round4/json/` no longer exists; only 3 PT JSONs committed under `docs/review_shots/round4/json/`). I therefore re-ran the extractor from historical commits exported with `git archive` to `/tmp` (no checkout/branch switch): `1bbf4fc` (Round4/4b, 2026-09-10), `672f427`, `9bebe0b`, `5d126fa` (main HEAD), `029f6d2` (this branch). The `1bbf4fc` reproduction is byte-for-byte equal (header + items) to the 3 committed Round4 PT JSONs (50666223, 50664997, 50664217), and its amount/line counts equal the Round4 report table for all 20.

## Per-file table (23 rows)

| # | file | invoice_no | R4 identical | verdict | amount (=NIV=Total=Value:) | cur | incoterm | lines | qty | GW kg | pkg JSON | pkg evidence (PDF) | evidence pages (NIV / GW / packing) | conflict / note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `40-D-26PT-404_50664923` | 50664923 | **NEW** | **pass** | 1,116.60 | USD | FCA Shanghai | 5 | 88 | 15.100 | 3 | 3 packing row(s)/unique packing no.; `total : 3` | p2 / p4 / p4 | — |
| 2 | `40-D-26PT-416_50666223` | 50666223 | yes (sha256 equal) | **pass** | 134.00 | USD | FCA Shanghai, packaging incl | 1 | 200 | 14.500 | 1 | 1 packing row(s)/unique packing no.; `total : 1` | p2 / p4 / p4 | — |
| 3 | `50-D-26PT-408_50664997` | 50664997 | yes (sha256 equal) | **pass** | 1,600.03 | USD | FCA Willershausen | 53 | 345 | 111.262 | 2 | 2 unique Shipping-unit IDs; `total : 2` | p8 / p11 / p12 | — |
| 4 | `50-D-26PT-421_50666072` | 50666072 | yes (sha256 equal) | **pass** | 681.26 | USD | FCA Willershausen | 31 | 196 | 31.177 | 2 | 2 unique Shipping-unit IDs; `total : 2` | p6 / p8 / p9 | — |
| 5 | `50-D-26PT-422_50665593` | 50665593 | yes (sha256 equal) | **pass** | 83.60 | USD | FCA Worms | 2 | 13 | 7.680 | 1 | 1 unique Shipping-unit IDs; `total : 1` | p2 / p3 / p4 | — |
| 6 | `50-D-26PT-423_50665862` | 50665862 | yes (sha256 equal) | **pass** | 319.80 | USD | FCA Worms | 2 | 98 | 18.880 | 1 | 1 unique Shipping-unit IDs; `total : 1` | p2 / p3 / p4 | — |
| 7 | `90-C-26PT-405_50654372` | 50654372 | **NEW** | **pass** | 52,165.90 | USD | FCA Worms | 261 | 7116 | 2,712.860 | 30 | 30 unique Shipping-unit IDs; `total : 30` | p34 / p38 / p43 | — |
| 8 | `90-C-26PT-405_50654373` | 50654373 | **NEW** | **pass** | 1,456.00 | USD | FCA Worms | 1 | 800 | 65.000 | 1 | 1 unique Shipping-unit IDs; `total : 1` | p2 / p3 / p4 | — |
| 9 | `90-S-26PT-407_50663797` | 50663797 | yes (sha256 equal) | **pass** | 4,509.80 | USD | FCA Hangzhou | 10 | 2740 | 239.400 | 5 | 5 packing row(s)/unique packing no.; `total : 5` | p3 / p5 / p5 | — |
| 10 | `90-S-26PT-407_50663901` | 50663901 | yes (sha256 equal) | **pass** | 20,053.84 | USD | FCA Hangzhou | 4 | 208 | 895.920 | 4 | 4 unique Shipping-unit IDs; `total : 4` | p2 / p3 / p4 | — |
| 11 | `90-S-26PT-409_50663231` | 50663231 | yes (sha256 equal) | **needs_gold** | 14,918.40 | USD | FCA Shanghai | 4 | 20160 | 4,100.000 | 12 | 1 packing row(s)/unique packing no.; `total : 12` | p2 / p4 / p4 | total_pkg: JSON 12 · PDF-supported unique packing units = 1 (single Packing-details row `22445380/272104738  1  P.13 Folding Box with Euro Pallet`, 3,679.200/4,100.000 kg, 1,200/800/1070 MM, p.4; same single packing no. on the line page p.2) vs PDF summary `P.13 Folding Box with Euro Pallet : 12` / `total : 12` (p.4). PDF self-contradicts; cannot determine true count from the PDF → needs BL/arrival-notice/forwarder packages. All other fields verified OK. |
| 12 | `90-S-26PT-410_50662910` | 50662910 | yes (sha256 equal) | **pass** | 14,980.86 | USD | FCA CHENGDU | 5 | 430 | 1,280.304 | 5 | 5 unique Shipping-unit IDs; `total : 5` | p2 / p3 / p4 | — |
| 13 | `90-S-26PT-411_50664363` | 50664363 | yes (sha256 equal) | **pass** | 21,879.36 | USD | FCA CHENGDU | 10 | 720 | 1,906.000 | 10 | 10 unique Shipping-unit IDs; `total : 10` | p3 / p4 / p6 | — |
| 14 | `90-S-26PT-412_50663621` | 50663621 | yes (sha256 equal) | **pass** | 5,221.44 | USD | FCA CHENGDU | 2 | 144 | 356.576 | 2 | 2 unique Shipping-unit IDs; `total : 2` | p2 / p3 / p4 | — |
| 15 | `90-S-26PT-413_50664949` | 50664949 | yes (sha256 equal) | **pass** | 592.00 | USD | FCA Hangzhou | 4 | 500 | 46.800 | 2 | 2 packing row(s)/unique packing no.; `total : 2` | p2 / p4 / p4 | — |
| 16 | `90-S-26PT-414_50665615` | 50665615 | yes (sha256 equal) | **pass** | 7,150.08 | USD | FCA Jingshen | 8 | 96 | 1,721.600 | 8 | 8 packing row(s)/unique packing no.; `total : 8` | p3 / p5 / p6 | — |
| 17 | `90-S-26PT-415_50664640` | 50664640 | yes (sha256 equal) | **pass** | 3,881.76 | USD | FCA Dongguan | 1 | 48 | 132.016 | 1 | 1 unique Shipping-unit IDs; `total : 1` | p2 / p3 / p4 | — |
| 18 | `90-S-26PT-417_50664925` | 50664925 | yes (sha256 equal) | **pass** | 2,169.60 | USD | FCA Tianjin | 6 | 480 | 71.640 | 6 | 6 packing row(s)/unique packing no.; `total : 6` | p2 / p4 / p4 | — |
| 19 | `90-S-26PT-418_50664217` | 50664217 | yes (sha256 equal) | **pass** | 41,674.97 | USD | FCA Penang | 11 | 957 | 1,664.900 | 11 | 11 unique Shipping-unit IDs; `total : 11` | p3 / p4 / p6 | — |
| 20 | `90-S-26PT-418_50664379` | 50664379 | yes (sha256 equal) | **pass** | 19,981.44 | USD | FCA Penang | 2 | 144 | 233.700 | 2 | 2 unique Shipping-unit IDs; `total : 2` | p2 / p3 / p4 | — |
| 21 | `90-S-26PT-419_50665577` | 50665577 | yes (sha256 equal) | **pass** | 2,154.00 | USD | FCA Hangzhou | 1 | 200 | 48.000 | 1 | 1 packing row(s)/unique packing no.; `total : 1` | p2 / p4 / p4 | — |
| 22 | `90-S-26PT-419_50665578` | 50665578 | yes (sha256 equal) | **pass** | 730.80 | USD | FCA Hangzhou | 4 | 340 | 32.300 | 3 | 3 packing row(s)/unique packing no.; `total : 3` | p2 / p4 / p4 | — |
| 23 | `90-S-26PT-419_50665811` | 50665811 | yes (sha256 equal) | **pass** | 2,575.68 | USD | FCA Hangzhou | 1 | 48 | 82.336 | 1 | 1 unique Shipping-unit IDs; `total : 1` | p2 / p3 / p4 | — |

For all 22 pass rows: every JSON field above equals the print; header.amount = sum(lines) = `Net invoiced value of goods` = `Total **` = `Value:` (no unit×qty substitution: printed amount = qty×price on every line anyway); GW = `Gross Weight:` = packing footer gross = Σ packing-row gross; every line has origin + HS equal to print (0/429 missing); per-HS line sums equal the printed tariff block; pkg = unique Shipping-unit IDs (where printed) = unique packing rows = `total : N`.

## Soft items — answers

### 1. 50663231 (90-S-26PT-409) — pkg → **needs_gold** (not pass)
- PDF p.4 `Packing details` has exactly **one** row: `22445380/ 272104738 · 1 · P.13 Folding Box with Euro Pallet · 3,679.200 kg · 4,100.000 kg · 1,200/800/1070 MM · 14,918.40 USD`. No `Shipping unit` section. The line page p.2 shows the same single packing no. 272104738 with gross 4,100.000 on the delivery row.
- The same page prints `P.13 Folding Box with Euro Pallet : 12` and `total : 12` (verified on 200-dpi render; the row count really is `1`, the summary really is `12` — not a text-layer artifact; OCR agrees).
- In every other P.13/carton file of this batch (50663797, 50664949, 50665615, 50665577, 50665578, 50664923, 50666223, 50664925) each unit has its own packing-no. row with qty 1 and `total : N` = number of rows. 50663231 is the only file among the 23 (and among all 20 archive PDFs) where they disagree.
- Rule 5: pkg = unique packing units; fallback to `total : N` only if it gives the true count. Here the unique-unit count from the detail is **1**, the fallback gives **12** → the fallback is *not* verifiable from the PDF. Plausibility (≈3.7 t net on one 1200×800×1070 folding-box pallet is well beyond a normal euro-pallet load, whereas 12 units ≈ 340 kg each is normal) leans toward 12, but that is inference, not print. **Correct pkg cannot be determined from this PDF**; confirm packages from BL / arrival notice / forwarder (none in this batch). Until then JSON `total_pkg = 12` should not be accepted as pass. (Round4 also produced 12 for this identical file; Round4's pass did not catch the contradiction.)
- Recommendation for the rule (not changed): when no Shipping unit exists and Σ packing rows ≠ `total : N`, raise needs_gold instead of a soft note.

### 2. 50664217 (90-S-26PT-418) — HS 84672920 → **JSON faithful to print; pass**
- The PDF prints `MY 84672920` (8 digits) on **two** lines, not one: line 6 `22449779/140100080058418998 · 0.601.9E0.0C1 · GDR 12V-EC (2.0Ah x · 60 pcs · 87.77 · 5,266.20` (p.2) and line 11 `22449917/140100080058417403 · 0.601.9E0.0C1 · 60 pcs · 5,266.20` (p.3). All other 9 lines print `MY 8467290000`. Verified on a 300-dpi crop and OCR.
- Tariff block p.4 lists both: `8467290000 · 1,166.500 KG · 31,142.57 USD` and `84672920 · 322.400 KG · 10,532.40 USD` (= 2×5,266.20). JSON has `84672920` on exactly lines 6 and 11 and `8467290000` elsewhere → faithful. (The Tools summary saying "one HS 84672920" is slightly off: it is 2 lines of the same material.) Whether customs needs a 10-digit code for 0.601.9E0.0C1 is a business decision, not an extraction error.

### 3. 50665615 (90-S-26PT-414) — incoterm / departure country → **JSON faithful; pass**
- p.3 under `Total 7,150.08 **` the PDF prints exactly `FCA Jingshen` (300-dpi crop, OCR agrees). JSON `FCA Jingshen` = print. Whether the vendor meant another place is not decidable from the PDF; keep as printed.
- Departure country: on p.1 the `Departure country` label **is not printed at all** (the whole field is absent, not just an empty value; other files print e.g. `Departure country China`). Not an extracted field; all 8 lines carry origin CN + HS 8-digit as printed.

## Byte-identity & regression check

**Byte identity: confirmed.** 20/23 sha256 equal to the archived Round4 PT samples; the 3 new files have no counterpart in the archive:

| file | sha256 | vs archive |
|---|---|---|
| `40-D-26PT-404_50664923` | `66a4c75f61214380f1d453eb1f0287e3bcbf5dbfc7fa8fd4c66b46e98ab677f7` | **new (not in archive)** |
| `40-D-26PT-416_50666223` | `3f65b0df17d0a99cefe249bea3ee1a37d5ad30cdb8421808c1c5b86f5c924de8` | identical |
| `50-D-26PT-408_50664997` | `7210e917f7e92f1de10239563946824c5ca512a20c293ff6a858e119979c1899` | identical |
| `50-D-26PT-421_50666072` | `c6558ce0eceab3f82276d6e5dfaed5abde6e5c70a2b64f4bc575953f3cc96027` | identical |
| `50-D-26PT-422_50665593` | `6d91b9cd138bf82f42c21e8bfeeaded5f885bdc201df98a2a3f9bfa88b18361d` | identical |
| `50-D-26PT-423_50665862` | `3060702f37c7b94ea656f521cb2ba52c2d0a339aafab1ce5603b3149f68ddb97` | identical |
| `90-C-26PT-405_50654372` | `573eb71d716202590d2017c717e24c6e9d1af0d6693b27a8b8e7361371cdaa3c` | **new (not in archive)** |
| `90-C-26PT-405_50654373` | `3bd8532aa182b2be7ad528c631d975c3b2a1cbd3b89f5b7eabf4ea50c0340662` | **new (not in archive)** |
| `90-S-26PT-407_50663797` | `b30de2ebd8b6eb8ee702372487b9265cf2a2fcea0a86f34af27dad42a8107f5f` | identical |
| `90-S-26PT-407_50663901` | `d946b85e2d8346c76ecf6d79f1e47648f4ec6ac342486c566408bce72f3d056b` | identical |
| `90-S-26PT-409_50663231` | `2c218f6a19e3800cc86ca9b6a9d6c290da5493251fbdf80ee625e80a2c7a3e58` | identical |
| `90-S-26PT-410_50662910` | `065e51c028d6d4cf7f895e758499367faef539bfeb2d480184095a5a026180eb` | identical |
| `90-S-26PT-411_50664363` | `aeb1eca4a96307ece0ce3a8d9b9a03b634f299c8e662bb015bd82e32efeb29ff` | identical |
| `90-S-26PT-412_50663621` | `edab3b3b4d32f8a7e8cd1e12294b938b1baf7ac4a4ba21de771cd44784b2c823` | identical |
| `90-S-26PT-413_50664949` | `207e1549796bd28f91a5c5e294e10927d682d0aac858367ae4901d9dffe69147` | identical |
| `90-S-26PT-414_50665615` | `6ee95738de985e91ac92b310cfa3fd4d7cb3ff006160213bb5e8651e38803a7a` | identical |
| `90-S-26PT-415_50664640` | `b174cc6589ecc63bcb82d2d2b1e22a969ea00218cbc03dc1ec99dbdb50176de0` | identical |
| `90-S-26PT-417_50664925` | `395e0e473db4cee97a0068d0576e03e6c32c32194f35c966ebc1432c8a8d3d59` | identical |
| `90-S-26PT-418_50664217` | `21ee586300b6087658b3b69959d25b06934e4fd4f9097baadcd080b4eea6a921` | identical |
| `90-S-26PT-418_50664379` | `6c0ba1e8d74331dddf90fa02a9e193d339f8a44c19bfedc14ad6674a493b5243` | identical |
| `90-S-26PT-419_50665577` | `db84e4823501102f37d216039f6f72f22a25cecd35d66454c6a98625548d2048` | identical |
| `90-S-26PT-419_50665578` | `3a9b5766731c32a4f20bd5af741d1e4c49f5524b47877daca037dae511e52c11` | identical |
| `90-S-26PT-419_50665811` | `d456ed022de4192b8a0c8cbb6fbf8a75bd447ca48625e81bbbf4b76e6994cae4` | identical |

**Regression (Round4 `1bbf4fc` reproduction vs current JSON, 20 identical files):** invoice_no, amount, currency, incoterm, GW, line count, total qty and every line's part_no/qty/amount/origin/HS are **unchanged on all 20**. The only changed field is **total_pkg on 11 of the 20**:

| invoice_no | Round4 pkg | now | PDF evidence (verified) | changed by |
|---|---|---|---|---|
| 50666223 | None | 1 | 1 packing row(s)/unique packing no.; `total : 1` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50666072 | None | 2 | 2 unique Shipping-unit IDs; `total : 2` (p9) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50663901 | None | 4 | 4 unique Shipping-unit IDs; `total : 4` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50662910 | None | 5 | 5 unique Shipping-unit IDs; `total : 5` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50664363 | None | 10 | 10 unique Shipping-unit IDs; `total : 10` (p6) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50663621 | None | 2 | 2 unique Shipping-unit IDs; `total : 2` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50664640 | None | 1 | 1 unique Shipping-unit IDs; `total : 1` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50664925 | None | 6 | 6 packing row(s)/unique packing no.; `total : 6` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50664217 | None | 11 | 11 unique Shipping-unit IDs; `total : 11` (p6) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50664379 | None | 2 | 2 unique Shipping-unit IDs; `total : 2` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |
| 50665811 | None | 1 | 1 unique Shipping-unit IDs; `total : 1` (p4) | `9bebe0b` (2026-09-22, *Fix PT Gloria total_pkg when only Shipping unit rows exist*) |

- In Round4 these 11 had **empty pkg** (would be a rule-5 conflict today; e.g. the committed Round4 JSONs for 50666223 and 50664217 have `total_pkg: null`), so the 2026-09-10 pass did not cover pkg for them. The new values were each re-verified against the PDF and are correct.
- These changes come from the earlier main-line fixes `672f427`/`9bebe0b`, **not** from this branch's new `total : N` fallback: main HEAD `5d126fa` and branch `029f6d2` give identical key fields on all 23 files (Tools' claim "no extracted value changed vs main" confirmed). The branch fallback never changes a value in this batch because every no-Shipping-unit file already had a matching type summary — except 50663231, where main already returned 12 too.
- New files: at Round4 code 50654372 would have been pkg 10 (now 30 = 30 unique SU IDs = 10+4+7+6+3 summary = `total : 30`), 50654373 and 50664923 empty (now 1 and 3, both verified).

## New files — full audit

- **50664923**: 5 lines, qty 88 (10+12+8+40+18), lines sum 1,116.60 = NIV = Total = Value:; all CN 82079071 as printed (p2); GW 15.100 (p4) = Σ 4.300+5.800+5.000; pkg 3 = 3 carton rows (273420303/304/305) = `total : 3`; FCA Shanghai. **pass**
- **50654372** (43 pages): 261 material rows parsed independently from pdftotext — 261/261 equal to JSON on part_no, qty, unit, price, amount, origin, HS (script `compare.py`); Σ lines 52,165.90 = NIV (p34) = Total = Value: (p38); total qty 7,116; 16 origins; every per-HS sum equals the printed tariff block (p37–38, 2,152.993 KG / 52,165.90 USD); OCR of all 43 pages finds every line's `CC HS` and amount. GW 2,712.860 (p38) = packing footer (p43) = Σ 30 SU gross. pkg 30 = 30 unique Shipping-unit IDs (p39–43) = `total : 30`. Also consistent with the user's `~/Downloads/PT INV LIST.xlsx` (50654372: 30 pkgs, 2712.86 kg, "20 PLT + 10 CTN"). FCA Worms. **pass**
- **50654373**: 1 line `1.619.M01.4EG wrist band Sport Wri · CN 61159500 · 800 pcs · 1.82 · 1,456.00` (p2); NIV = Total = Value: 1,456.00; GW 65.000; pkg 1 (SU 1010622633, `total : 1`); FCA Worms; matches `PT INV LIST.xlsx` (1 pkg, 65 kg). **pass**

## Other observations (non-blocking)

- Tools' report says 'Packages = Packing total : N (and = unique Shipping-unit count where printed)' and 'no needs_gold' — true for 22 files; wrong conclusion for 50663231 as above.
- Round4 artifacts: `out/round4/json/` (referenced by `reports/round4_pt_ma_bhc.md`) is missing from disk; only 3 PT Round4 JSONs survive in `docs/review_shots/round4/json/`. Regression baseline here was rebuilt from commit `1bbf4fc`.
- Nothing illegible in any of the 23 PDFs.
