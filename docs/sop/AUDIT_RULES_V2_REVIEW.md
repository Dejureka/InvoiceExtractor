# Validator v2 審核說明（給 Auditor）

分支 `feat/validator-audit-rules`（基於 main `22167b8`，回退 tag `backup/pre-audit-rules-v2`）。只改 `tools/validate_result.py`、測試與 SOP；`src/`、抽取行為、portable 都沒動。依據：`/workspace/handoff/audit_sop_review_20261123.md` §4 第 1～3 項＋`H_LINE_COUNT` 修正（4、5 不做）。

## 1. 新規則與等級

| 規則 | 等級 | 觸發 | 為什麼這個等級 |
|---|---|---|---|
| `H_PACKING_UNITS` | hard | MA（`ma_*`）pkg ≠ 不重複 packing key 數；shipment_first 首張用 shipment 全部發票的 key 聯集 | MA 的 pkg／GW 定義上就是同一張 PL key 表算出來的，不一致一定是錯 |
| `W_PACKING_UNITS` | warn | 同上，非 MA 格式（目前沒有格式會觸發） | 其他廠商可能 pallets／cartons 混算（package_mode），誤報風險中 |
| `H_PACKING_GW`／`W_PACKING_GW` | hard（MA）／warn | GW ≠ key 重量加總，超過容差（每個 key 印出末位一半的加總＋0.01）；容差內為 `W_ROUNDING` | 同上 |
| `H_PACKING_SHARED` | hard | 同一資料夾的不同發票出現同一個 key，但沒套 shipment_first；或套了但非首張沒把該 key 歸零。PDF／Excel twin 同發票號只算一張 | 重複計件；shipment_first（MA／BHC 共用 PL）正確套用時不會觸發 |
| `H_PRINTED_QTY` | hard | `total_quantity`（或 meta 的 `printed_total_quantity`／`labeled_quantity`）≠ 明細 qty 加總 | 只有在印出值可區分時才比：多數格式 `total_quantity` 就是加總，相等時不算「驗過」 |
| `W_PRINTED_QTY_MIXED_UOM` | warn | 同上但明細單位混雜（`pc.`／`pcs`／`PCS` 視為同一單位） | 有些廠商總數混算 cartons＋pcs |
| `W_NO_LABELED_TOTAL` | warn | 金額的印出總額沒抓到（以前默默略過）。note 會寫 qty 總數、列數是否也驗不到 | 不是錯，是「這張總額只能靠看圖」 |
| `H_PRINTED_AMOUNT`（擴充） | hard | Excel twin 沒有 TOTAL 列時，改用同發票 PDF twin 印的總額比 | 同一張發票的印出值；原本這種 twin 會變成 `W_NO_LABELED_TOTAL` |
| `H_LINE_COUNT`（修正） | hard | 列數跟**獨立來源**比：meta `printed_item_count`／`printed_line_count`／`item_count_printed`，或連續項次的最後一號（1 起算或 10 起算）；另保留 Summary `item_line_count` ≠ Lines 列數 | 以前是 `len(items)` 跟自己比，永遠不會觸發 |
| `W_LINE_COUNT_UNVERIFIED` | warn | 沒有獨立列數，也沒有任何印出總額比對。若同列已有 `W_NO_LABELED_TOTAL`，改寫在它的 note，不另列 | 不假造列數；有金額總額時漏行會被 `H_PRINTED_AMOUNT` 抓到，所以不另外提醒 |
| `H_OCR_FAILED` | hard（不因 needs_gold 降級） | `text_backend` 含 `ocr_failed`／`ocr_timeout`、meta 記錄 timeout、或發票列 `needs_ocr`＝True；BL extract 也查 | 這列的值完全沒跟文字比過，不可默默 pass |
| `H_NEEDS_GOLD_FLAG` | hard（不降級） | `needs_gold_fields` 有值，但 `needs_gold`＝False 或 `checker_verdict`＝pass／ok | 旗標不一致會讓需人工的列混進 pass |
| `W_NEEDS_GOLD_FLAG` | warn | `needs_gold`＝True 但沒有欄位原因 | 有標記但不知道看哪裡 |

既有規則代碼與行為不變（MA／PT／SOE 缺 HS＝hard、BHC／eBike＝warn 照舊；shipment_first 非首張沒附註仍 hard，已加測試鎖住）。數值比較全部用 Decimal，沒有寫死任何案例值。

## 2. 回歸結果（8 批已審核資料，本機無 tesseract；改前／改後 findings 在 `/workspace/handoff/audit_rules_v2/regress/`）

| 批次 | 發票 | 改前 hard／warn | 改後 hard／warn | 抽取 diff | 新增 finding | 分類 |
|---|---:|---|---|---:|---|---|
| ma3 | 184 | 0／14 | 0／14 | 0 | 無 | — |
| pt4 | 23 | 0／0 | 0／0 | 0 | 無 | — |
| bhc4 | 14 | 0／107 | 0／108 | 0 | `W_NO_LABELED_TOTAL` VKT26073 | 真的覆蓋缺口：`nidec_v1` 沒抓 PDF 印的 `Net Amount … USD 129,780.00`（加總本身正確）。要補需改 `src/`，本次範圍外 |
| bhc5 | 2 | 0／0 | 0／1 | 0 | `W_NO_LABELED_TOTAL` VKT26075 | 同上（nidec_v1） |
| bhc6 | 19 | 0／126 | 0／126 | 0 | 無（3 對 Excel twin 改用 PDF TOTAL 比對，全部相符） | — |
| ebike1 | 18 | 0／22 | 0／22 | 0 | 無 | — |
| soe2 | 10 | 0／0 | 0／0 | 0 | 無 | — |
| maak | 3 | 0／0 | 0／0 | 0 | 無 | — |

已審核資料上新規則 **hard 誤報＝0**。warn 只多 2 筆，都不是誤報，是 nidec 格式的真實覆蓋缺口。bhc4 的 3 對 Excel twin（117-BHCTW-26K-41、121-BHCTW-26K-37）與 bhc6 的 117-BHCTW-26K-43 原本會多出 `W_NO_LABELED_TOTAL`，改用 PDF twin 總額後變成真的比對，結果相符。

`fixtures/validate_prefix`：MA 2000263342 仍 2 筆 `H_HS_MISSING`；2120411708 對照組 0 筆 HS；PT Gloria 5 張仍各 1 筆 `H_HDR_MISSING`（另加 `W_NO_LABELED_TOTAL`，因為當時版本還沒有標籤總額）。

測試：`tests/test_validate_result.py`＋新 `tests/test_validate_audit_rules.py` 88 passed；`tests/test_gold_regression.py` 16 passed；全套 pytest 508 passed／20 skipped（OCR）／3 failed（`test_gui_smoke.py` 本機沒有 tkinter，已知）。

## 3. 舊 conflict 現在抓不抓得到

重現檔在 `/workspace/handoff/audit_rules_v2/v2_caught/<case>/`（repo 內 `out/v2_caught/` 是同一份，out/ 不進 git）（`how.txt` 寫明怎麼重現；「忠實重跑」＝用修正前 commit 的程式重抽，「重建」＝在現有 extract 上做最小修改）。

| # | 案例 | 重現方式 | 新規則結果 | 舊規則 | 抓到？ | 原因 |
|---|---|---|---|---|---|---|
| R1-a | MA 2000262902 RB key 撞號（22→67 件） | 忠實重跑 `51d11ec`（eac7bc7^） | 無 | 無 | **否** | 當時沒輸出 packing key；把舊的截斷 key 補回去後，件數／GW 跟 key 一致（撞號讓兩邊一起錯），只有跨發票重疊觸發 `H_PACKING_SHARED` ×2（重建）。單張發票內的撞號仍要靠 PL 印出總數或看圖 |
| R1-b | MA 3rd 008（RB 110936597）、036（RB 111292965）重複計件 | 現行程式關掉 shipment 去重（重建 R1 行為） | `H_PACKING_SHARED` hard ×4 | `H_BL_TOTAL` ×4 | **是** | 不需要 BL 也抓得到；去重後的對照組 0 筆 |
| R1-c | MA AK 74096／097／098（50 件→40 件） | 忠實重跑 `27f76bf`（9e15c71^）＋現行 parser 不去重 | 忠實：無；重建：`H_PACKING_SHARED` hard ×2 | 無 | **部分** | 修正前的 parser 讀不到 `Gross HU Weight`，沒有 key 可比；現在有 key，同類錯（沒套 shipment_first）會被抓到。這票沒有 BL，`H_BL_TOTAL` 原本抓不到 |
| R1-d | PT round3 50666881／50666882／50659168、SOE 7091802382、BHC 6th case 11 DA15199998 GW、BHC 4th SATJG26011 GW | 歷史 snapshot | 無 packing 類 | `H_BL_TOTAL` ×3、`H_HDR_MISSING` ×1 | **否** | PT Gloria／SOE／BHC 格式沒輸出 packing key；要抓需改 `src/` 輸出 key（範圍外，未改）。BHC 兩個 GW 錯原本就被 `H_BL_TOTAL` 抓到 |
| R2-a | 鷺宮 T262288 漏第 22 行 | 忠實重跑 `bb5a7d8`（680b560^） | `H_PRINTED_QTY` hard（12,075 vs 12,074） | `H_PRINTED_AMOUNT` | **是** | 第二道網 |
| R2-b | BHC 4th MEH6J044 0 行 | 當時的 extract（`/workspace/bhc4`） | `H_PRINTED_QTY` hard（4,815 vs 0）＋`W_NO_LABELED_TOTAL` | `H_HDR_MISSING` ×2 | **是** | 以前金額沒標籤所以默默過 |
| R2-c | BHC 4th SATJG26011 只抽到 1／2 行 | 當時的 extract | `W_NO_LABELED_TOTAL` | `H_BL_TOTAL` ×2（只有件數） | **只提醒** | 金額標成 sum(lines)、沒有印出 qty／列數，漏行本身驗不到；warn 會要求 Auditor 看合計區 |
| R2-d | PT 4th 23 張 `labeled_amount` 全空 | 忠實重跑 `029f6d2`（aa7deb7^） | `W_NO_LABELED_TOTAL` ×23 | 無 | **是** | 這筆 conflict 本來就是「沒驗到卻沒講」 |
| R2-e | BHC 3rd OK20260921 廠商 qty 打錯 | 現行程式跑原始 XLS | 無 | `H_DATE`（無關） | **否** | 結構化 qty 與加總都是 20,750，錯的 10,750 只在附註；屬原始文件矛盾（C 類），留給 Auditor |
| R3-a | T261955 掃描檔、沒 tesseract | 現行 CLI | `H_OCR_FAILED` hard＋`W_NEEDS_GOLD_FLAG`＋`W_NO_LABELED_TOTAL` | `H_HDR_MISSING` ×6 | **是** | |
| R3-b | BHC 6th T261565 OCR 逾時 | 現行 CLI，模擬 subprocess TimeoutExpired | `H_OCR_FAILED` hard＋`W_NEEDS_GOLD_FLAG`＋`W_NO_LABELED_TOTAL` | `H_HDR_MISSING` ×6 | **是** | 逾時在 backend 記成 `+ocr_failed`；正常跑（文字層）0 筆新 finding |
| R3-c | `INVOICE_OCR_TIMEOUT` 非數字造成 import crash | 忠實重跑 `8a1cfcd`（0c9ba89^） | — | — | **不適用** | 程式直接 crash、沒有 Result 列，不會有「默默 pass」 |
| R3-d | QDEX2609010 有欄位旗標但 `needs_gold`＝False | 當時的 PDF／Excel extract＋重建 | `H_NEEDS_GOLD_FLAG` hard ×2（重建 ×1） | `W_TWIN`、`W_TWIN_PKG_BLANK` | **是** | |

小結：報告 §4 估第 1～3 項可多抓約 15 筆；實測新規則抓到 7 案（R1-b、R2-a、R2-b、R2-d、R3-a、R3-b、R3-d），部分 1 案（R1-c），只提醒 1 案（R2-c），抓不到 3 案（R1-a、R1-d、R2-e），1 案不適用（R3-c）。抓不到的主因：PT／SOE／BHC 沒輸出 packing key、撞號讓兩邊一起錯、原始文件本身矛盾。

## 4. SOP 改了什麼（`docs/sop/AUDIT_SOP.md`）

- 標頭：v2 草稿狀態；退回方式加 tag `backup/pre-audit-rules-v2`，舊的 `AUDIT_REVIEW.md`／`backup/pre-validate-result` 不動。
- §2：規則清單改成「Validator 負責的檢查」表（含 v2 新規則），並列出 validator 的已知限制（印出值是 parser 讀的、qty 總數多半驗不到、只有 MA 有 packing key、掃描值）。
- §3：Auditor 只留看圖：(a) 每列 hard／warn 給結論；(b) 合計區截圖；(c) 隨機抽行看圖（≥3 列或 10%，新格式第一批逐列）；(d) 掃描文件的值；(e) C 類判斷（原始文件矛盾、needs_gold 證據衝突、附註文字、OCR 邏輯審程式）；(f) pass 條件。
- §4 回歸：pytest 加 `tests/test_validate_audit_rules.py`；已審核資料 hard 必須 0、新 warn 要逐筆分類。
- 新 §5：廠商地雷（PT Gloria、SOE、MA、BHC、鷺宮、eBike）、實用清單、既定決定。
- `ADD_INVOICE_FORMAT.md` 第 8 步：pytest 指令加新測試檔；warn 也要逐筆說明，提醒新格式盡量填 `meta.labeled_amount`。

## 5. 想請 Auditor 決定的

1. `W_NO_LABELED_TOTAL` 只在**金額**總額沒抓到時出現；qty 總數驗不到（多數格式）只寫在 note，不另列，以免每張發票都多一筆 warn。可以嗎？
2. `W_LINE_COUNT_UNVERIFIED` 併進 `W_NO_LABELED_TOTAL` 的 note（一列一筆 warn）。可以嗎？
3. 非 MA 的 packing 檢查用 warn。目前沒有其他格式輸出 packing key，所以實際上不會觸發。
4. 後續（要改 `src/`，本次沒做）：`nidec_v1` 補抓 `Net Amount` 當 `labeled_amount`；PT Gloria／SOE 輸出 Shipping unit／RB key 到 `meta.packing_units`。
