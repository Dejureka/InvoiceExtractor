# AuditSOP（現行）— 全列硬校驗＋Auditor 看圖

**狀態：現行流程 v2（2026-11-24 起生效）。** Auditor 2026-11-24 審核通過（`5b03d36`）＋其補充條款（本版已納入）。v2 把更多「機器能比的」搬進 `tools/validate_result.py`，Auditor 只留下必須看圖的部分。  
**退回方式：**
- 退回 v1：程式與本文件回到 tag `backup/pre-audit-rules-v2`。
- 退回舊流程：不跑 validator，照 [`AUDIT_REVIEW.md`](AUDIT_REVIEW.md) 步驟 1～6 審核（legacy／備援；程式 tag `backup/pre-validate-result`，c0266c6）。

`tools/validate_result.py` 與 `tools/regression_batches.py` 只在原始碼 repo 使用，**刻意不放進 portable**（不在 `src/invoice_extractor/`，PyInstaller spec 不會收）。

---

## 1. 產出同一次抽出的 Excel＋JSON

```bash
cd /workspace/InvoiceExtractor
PYTHONPATH=src python3 -m invoice_extractor <PDF/資料夾…> --out out/audit/Result.xlsx
PYTHONPATH=src python3 -m invoice_extractor <同一批 PDF/資料夾…> --out out/audit/extracts.json
```

（不要加 `--record-run`。）

## 2. 跑全列硬校驗（validator 負責的部分）

```bash
python3 tools/validate_result.py out/audit/Result.xlsx --extract-json out/audit/extracts.json --out out/audit/findings.xlsx
# 也可輸出 .md；只有 JSON 時：python3 tools/validate_result.py --extract-json <檔或資料夾> --out findings.md
```

- 每個 finding 一列：`status`（ok／warn／hard）、`rule_id`、`invoice_no`、`row`、`field`、`expected`、`actual`、`page`、`position`、`note`；另有 Summary 分頁。有任何 hard → exit code 1。
- `needs_gold` 欄位上的值類發現降為 warn（`H_OCR_FAILED`、`H_NEEDS_GOLD_FLAG` 例外，永遠 hard）。
- 船名、航次、ETA／ETD、CBM、櫃號一律不檢查。

### 2.1 Validator 負責的檢查（Auditor 不必再人工重做）

| 檢查 | 規則 | 等級 |
|---|---|---|
| 表頭必填 invoice_no／date／currency／amount／pkg／GW | `H_HDR_MISSING` | hard |
| 日期可解析、ISO 4217 幣別、首張 pkg 為正整數 | `H_DATE`、`H_CURRENCY`、`H_PKG_INTEGER` | hard |
| 明細料號／qty／amount 不可空 | `H_LINE_MISSING` | hard |
| HS：MA／PT／SOE 缺 HS＝hard，BHC／eBike＝warn；位數 | `H_HS_MISSING`／`W_HS_MISSING`、`H_HS_FORMAT` | hard／warn |
| qty×單價≈金額（容差依印出位數，Auditor 2026-11-20） | `H_LINE_MATH`、`H_PRICING_UNIT` | hard |
| 明細金額加總＝印出的標籤總額（0.01） | `H_PRINTED_AMOUNT`（差 ≤0.01 為 `W_ROUNDING`） | hard |
| **v2** Excel twin 沒有 TOTAL 列時，用同發票 PDF twin 印的總額比對 | `H_PRINTED_AMOUNT`（note 註明 from twin） | hard |
| **v2** 沒抓到印出總額 → 不再默默略過 | `W_NO_LABELED_TOTAL` | warn |
| **v2** 明細 qty 加總＝印出的 qty 總數（只在抽出能區分「印出值」時；單位混雜降 warn） | `H_PRINTED_QTY`／`W_PRINTED_QTY_MIXED_UOM` | hard／warn |
| **v2** 列數：跟**獨立來源**比（印出的項目數，或連續項次的最後一號）；Summary 列數＝Lines 列數 | `H_LINE_COUNT` | hard |
| **v2** 沒有獨立列數、也沒有任何印出總額可比 | `W_LINE_COUNT_UNVERIFIED`（若已有 `W_NO_LABELED_TOTAL`，併在它的 note，不另列） | warn |
| 項次連續 | `H_LINE_POS` | hard |
| pkg／GW＝印出值（依格式規則）；shipment_first 非首張 0＋附註（沒附註＝hard） | `H_PRINTED_PACKING`、`H_HDR_MISSING` | hard |
| **v2** pkg＝不重複 packing key（RB／HU）數；shipment_first 首張用整個 shipment 的 key 聯集 | `H_PACKING_UNITS`（MA）／`W_PACKING_UNITS`（其他） | hard／warn |
| **v2** GW＝各 key 重量加總（容差＝每個 key 印出末位的一半加總＋0.01） | `H_PACKING_GW`（MA）／`W_PACKING_GW`（其他），容差內 `W_ROUNDING` | hard／warn |
| **v2** 同一資料夾多張發票共用同一 key，卻沒套 shipment_first（或非首張沒歸零） | `H_PACKING_SHARED` | hard |
| GW 不可 ≤ NW 合計 | `H_GW_NW` | hard |
| 同 BL 的 pkg／GW 合計＝BL | `H_BL_TOTAL`、`H_BL_TOTAL_CONFLICT` | hard |
| **v2** OCR 失敗／逾時／仍需 OCR → 這列**沒驗到** | `H_OCR_FAILED` | hard |
| **v2** `needs_gold_fields` 有值但 `needs_gold`＝False 或 verdict＝pass | `H_NEEDS_GOLD_FLAG` | hard |
| **v2** `needs_gold`＝True 但沒寫原因欄位 | `W_NEEDS_GOLD_FLAG` | warn |
| 同批發票號不可重複；Result.xlsx 與 JSON 逐格一致 | `H_DUPLICATE`、`H_XLSX_DIFF`、`H_XLSX_TYPE`、`H_ORPHAN_LINE` | hard |
| 依文件規則編碼的例外 | `W_TWIN`、`W_TWIN_PKG_BLANK`、`W_GW_FROM_BL`、`W_PN_BLANK_PRINTED`、`W_LINE_NW`、`W_WATERMARK`、`W_DUAL_CURRENCY`、`W_VENDOR_TOTAL` | warn |

**Validator 的已知限制（所以第 3 節還是要看圖）：**
- 「印出值」是 parser 自己讀的。錨點讀錯（把 Net 當 Gross、單價當總額、cartons 當 pallets），兩邊會一起錯、validator 看不出來。
- 多數格式的 `total_quantity` 就是明細加總，qty 總數只有在格式抓到印出值且跟加總不同時才驗得到；漏行主要靠金額總額。
- 只有 MA（`ma_*`）有 packing key（`meta.packing_units`）。PT Gloria、SOE、BHC 的件數／GW 沒有 key 可比，仍靠印出值、BL 合計與看圖。
- **新格式開始輸出 packing key 時：** 該格式第一批的每一列 `W_PACKING_*`，Auditor 都要對圖確認；確定沒有誤報後，才把該格式升成 hard（加進 `H_PACKING_*` 的格式清單）。
- 表頭 invoice_no／date／currency／Incoterms：validator 只檢查格式與 xlsx／JSON 一致，看不出 parser 是不是讀錯欄（雙幣別特別容易），所以要靠 §3(b) 看圖。
- 單張 MA 發票內的 key 撞號（R1-a 類）會讓 pkg 跟 key 數一起錯，validator 抓不到，要靠 §3(b) 對 PL 印出的總件數。
- 掃描檔上的數值只存在圖上。

## 3. Auditor 審核（只留必須看圖的部分）

a. **validator 每一列 hard／warn 都要有結論**（依 page／position 對照）：hard 必須修掉或逐筆說明；warn 要寫明是已知例外還是要修。  
b. **每張發票的合計區截圖**（pkg／GW／amount，有印 qty 總數也一起看）：確認 parser 抓的「印出值」就是對的那個數字（Gross 不是 Net、Final 不是單價、pallets 不是 cartons）。`W_NO_LABELED_TOTAL` 的發票，總額只能靠這一步。  
   - **`W_NO_LABELED_TOTAL` 且 note 寫「列數未驗」：** 在圖上數明細列數，跟 LINE（Lines 列數／`item_line_count`）比。這是 R2-c（SATJG26011 只抽到 2 行中的 1 行）唯一抓得到的地方。  
   - **單張 MA 發票：** PL 有印總件數時，pkg 要跟它比。這能抓到 R1-a 類 key 撞號（pkg 跟 key 數一起錯）。  
   - **表頭：** 除了合計區，同一次截圖審核也要看 invoice no.、日期、幣別、Incoterms 是否跟圖一致。validator 只驗格式與 xlsx／JSON 一致，看不出 parser 讀錯欄，雙幣別文件特別容易出錯。  
c. **每張發票隨機抽查明細看圖**：至少 3 列或 10%（無條件進位），取較大者；不足 3 列全看。**不可只抽頭尾**。新格式第一批逐列全看。**多頁發票每頁至少抽 1 列，且一定要含換頁處的明細（前一頁最後一列＋下一頁第一列）**，因為漏行最常發生在換頁；這些列算在「3 列或 10%」裡面，不是另外加。抓的是「數字彼此對得上但其實錯」：PN 換位、描述跑進 PN 欄、形近字（`-576`／`-57G`）。  
d. **掃描文件上的值**（掃描提單 BL No.／件數／GW、OCR 讀出的值）：只能看圖判斷，例如千位被底紋吃掉（`774.5`／`1,774.5`）、`C` 讀成 `0`。INV／PL 合計只能佐證，不能單獨定案。  
e. **validator 管不到的判斷（報告 C 類）**：  
   - 原始文件本身矛盾（廠商打錯、大寫金額與數字不一、email 與 PL 不同）：用哪個值由使用者／Auditor 決定，記在 note；已成規則的用 `W_VENDOR_TOTAL`、`W_LINE_NW`。  
   - needs_gold 的證據衝突（例：PT 50663231 pkg 12 只是建議值）：要 BL／到貨通知才能解。  
   - 附註文字是否正確、是否誤導。  
   - OCR 投票／規則邏輯的風險：審程式＋單元測試，不是逐列檢查。  
f. **pass 條件：** validator hard＝0（或逐筆有結論）、warn 都有解釋、b～d 抽查乾淨。抽查抓到錯誤時，先在 `tools/validate_result.py` 補一條能抓到它的規則（附測試），重跑再重審。

舊流程的圖文對照、角色分工、反例清單仍適用（見 `AUDIT_REVIEW.md` 的「反例」「角色」）。

## 4. 回歸（改任何格式或 validator 前後）

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_validate_result.py tests/test_validate_audit_rules.py tests/test_gold_regression.py
python3 tools/regression_batches.py --baseline out/regress/baseline --report out/regress/report.md
# 第一次或在已審核通過的版本上重建基線：
python3 tools/regression_batches.py --baseline out/regress/baseline --save-baseline --report out/regress/baseline-report.md
```

- `tests/gold/` 是已審核批次（MA 3rd、PT 4th、BHC 4th～6th、eBike 1st、SOE 2nd、MA AK 74096）凍結的 Result 欄位；不含 needs_gold 及本機無法 OCR 的檔案。差異必須是 0。
- 回歸報告逐列列出（批次、發票、欄位、基線值、現值），非 0 要逐筆說明給 Auditor。
- 已審核批次上 validator 的 hard 必須是 0；新規則在已審核資料上的 warn 要列在報告裡逐筆分類。
- 本機沒有 tesseract 時，OCR 檔案會跳過，不算回歸。

## 5. 參考：廠商地雷與既定決定

（整理自 2026-11-23 audit 報告回顧 §3，細節與出處見 `/workspace/handoff/audit_sop_review_20261123_inventory.md` §4。）

### 5.1 廠商地雷

- **PT Gloria：** 件數先數不重複的 Shipping unit ID，再看 Packing `total : N`，再看型別加總。有印出證據但 pkg 空白＝conflict。沒有 Shipping unit 且數量不一致 → needs_gold（50663231）。金額用 Net invoiced value 標籤。
- **SOE：** PN 要在 invoice、Customer PN、cargo list、transport order 之間對帳。字母優先只限 G/6。不可從 email 或範圍外的 BL 回填。
- **MA：** WithPeriod 的「Amount … in TWD」會拆在不同列。NoPeriod 的 RB key 是兩段數字串接。共用 RB／HU → shipment_first，放在發票號最小那張。AK 用 `Gross HU Weight`，後面的 18 位 HU 也要算。
- **BHC：** 中文檔名與合併文件是配對證據。TVL 提單的 cargo 件數就在櫃數旁邊。JIF 掃描的底紋會吃掉數字。依印出的 invoice ref 選 waybill。Topband PN＝DRAWING NO.。Hailiang 用 PO NO 和 KG。Wolong 以數字總額為準、不用大寫。Sanhua 的 PDF 可能沒印 PN。
- **Saginomiya（鷺宮）：** 單位可能是 `pc.` 或 `pcs`。同時印 cartons 和 pallets 時用 pallets。PL 的合計在 NW 欄下，所以 GW 取自 BL。
- **eBike：** 歐式千分位。EUR＋HUF 文件用 EUR。單價＝金額／數量，取 6 位小數。Copy／NOT VALID 要加附註。

### 5.2 實用清單

- `AUDIT_REVIEW.md` 的「反例」清單與「角色」表。
- MA 3rd R2 shipment_first 審核步驟（`AUDIT_REVIEW.md` 第 88 行附近）。
- BHC 6th R4／R5 殘餘風險（`/workspace/bhc4audit/bhc_6th_round4_auditor_review.md`、`round5_auditor_check.md`）：部分出貨的 run 可能錯誤佐證被截斷的 GW；JIF clean-page 與 token OCR 用的是同一張圖。

### 5.3 既定決定

- 只審 Result 有的欄位；BL＝No.／Pkg／GW（2026-09-29）。
- 只有文字層空白或不可靠時才 OCR，並記錄 backend 標籤。
- 缺 HS：MA／PT／SOE＝hard，BHC／eBike＝warn。
- Gloria soft-miss 已廢除（2026-09-22）。
- BHC 6th case 8 只跑 KEE602；case 9 與 QDEX2609010 維持 needs_gold。
- eBike 單列 NW 照印出值保留。
- validator 與回歸工具只在 repo，不進 portable（使用者 2026-11-20）。

## 修訂紀錄

| 日期 | 說明 |
|------|------|
| 2026-11-24 | v2 轉為現行（Auditor 通過 `5b03d36`＋補充）：新格式 packing key 首批 `W_PACKING_*` 逐列對圖後才升 hard；§3(b) 加「列數未驗」數列數、MA 單張對 PL 印出總件數、表頭 invoice no.／日期／幣別／Incoterms 看圖；§3(c) 多頁每頁至少 1 列且含換頁處；`W_NO_LABELED_TOTAL` note 固定含「列數未驗」。 |
| 2026-11-24 | v2 草稿：新增 packing key 交叉比對（`H/W_PACKING_UNITS`、`H/W_PACKING_GW`、`H_PACKING_SHARED`）、印出 qty 總數（`H_PRINTED_QTY`、`W_PRINTED_QTY_MIXED_UOM`）、`W_NO_LABELED_TOTAL`、Excel twin 用 PDF twin 總額、OCR 失敗（`H_OCR_FAILED`）、needs_gold 旗標一致（`H/W_NEEDS_GOLD_FLAG`）；`H_LINE_COUNT` 改跟獨立來源比（修掉自己比自己）＋`W_LINE_COUNT_UNVERIFIED`。Auditor 只留看圖：合計區截圖、隨機抽行、掃描值、C 類判斷。加入廠商地雷與既定決定。說明見 [`AUDIT_RULES_V2_REVIEW.md`](AUDIT_RULES_V2_REVIEW.md)。 |
| 2026-11-20 | 明細列 qty×單價 容差改依印出位數（AK00074096 110／120／140 印出差 1 TWD → ok）；總額比對不變。 |
| 2026-11-20 | 新增：全列硬校驗 `tools/validate_result.py`＋金標回歸＋抽查規則（Invoice＋Auditor 共同議定）。舊流程保留為 `AUDIT_REVIEW.md`。 |
