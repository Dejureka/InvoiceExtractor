# FormatSOP — 新增一種發票抽取規則

**溝通名稱：`FormatSOP`**  
路徑：`docs/sop/ADD_INVOICE_FORMAT.md`  
對象：開發／維護規則的人（含 Grok Bot）。  
相關：審核見 [`AUDIT_REVIEW.md`](AUDIT_REVIEW.md)；日常操作見 [`USER_RUN.md`](USER_RUN.md)（溝通名稱 **`RunSOP`**）。

---

## 目標

為一種新的發票版式（或同一廠商的大改版）新增可離線執行的規則：能正確分類、抽出 Summary／Lines、硬校驗可擋假 pass，並留下可追溯的版次紀錄。

---

## 名詞

| 用語 | 意思 |
|------|------|
| `format_id` | 規則識別名，例如 `pt_gloria_v1`、`bitzer_v1`。對應 Python 模組 `src/invoice_extractor/formats/<id>.py`。 |
| **種子（seed）** | 把「這版規則的名片」寫進 SQLite（`data/invoice_formats.db`）：廠商、aliases、`version`、`match_hints`、`rules_json`、備註。由 `--init-db`／`seed_builtin_formats` 執行。種子 ≠ 另寫一套執行引擎；真正抽欄位的是模組裡的 `extract`／`match_score`。 |
| `match_score` | 依檔名＋內文關鍵字打分（0～1）。執行時在 `BUILTIN` 清單裡**每個 format_id 各自打分**，取最高且 ≥ 0.3 者。 |
| v1／v2 | 版式大變時開新模組（如 `pt_gloria_v2`）＋ DB `version=2`，**不覆蓋**舊版。目前沒有「先認廠商再選版次」的第二層；v1／v2 若同時存在，也是兩邊都打 `match_score`，誰高用誰（錨點必須能分開舊／新版式）。 |

---

## 流程（10 步）

### 1. 收樣本

- 至少 1～3 張 PDF（正常＋邊界）。
- 若公司既有 `PDFextract.xlsm`，標註對應 VBA Sub（例：PT → `PT_PDFextract`／`PT_Declaration`；MA 變體很多，一次只對一個 Sub＋樣本）。

### 2. 抽文字層

- 用工具內建文字層（優先 pdftotext／poppler；否則後備）產出對照用 `.txt`。
- **Excel 輸入**（`.xlsx`／`.xlsm`／`.xls`）：`.xlsx`/`.xlsm` 用 openpyxl；`.xls` 用 xlrd（`excel/xlrd`）。各 sheet 轉成列文字（`=== Sheet: … ===`＋儲存格 tab 分隔），再走**同一套** match_score／規則（`meta.source_kind=excel`）。不跑 OCR。
- **掃描件／文字層空或不可靠**（**OCR when the text layer is empty or unreliable**）：走離線 Tesseract OCR（`meta.text_backend=ocr/tesseract`；文字層不可靠＝殘留／亂碼層，backend 加 `+prefer_over_stale_layer`，亂碼層再加 `+mojibake_layer`，CLI 警告與 log 會寫出實際用的 OCR backend），再對 OCR 字串寫規則（**同一** rules_engine，不要另開 OCR-only format_id）。對照用 `.txt` 可從 OCR 輸出存檔。
- **圖片輸入**（`.jpg`／`.jpeg`／`.tif`／`.tiff`；`.png` 只收明確點選的單檔，資料夾不掃 PNG，避免吃到截圖）：沒有文字層 → 直接 OCR（小圖先放大到 ≥2000 px 寬），backend `ocr/tesseract+image`，再走同一套分類／規則（`meta.source_kind=image`）。BHC 4th case 3 `QDEX2609096.jpg`（TVL 青島提單照片）起適用；舊批 BHC 2nd case1 `QDEX2609010.jpg` 也會被讀到。
- **空白 Excel 範本**（只有表頭、數字儲存格 <3 個；例 `SSLJP0023526  MEH6J044.xls`、mega `DF_SFA006358 MEH6A036 IV PL.xls`）：配對時直接略過（`SKIP … (empty Excel template (no values) — skipped)`），不產生空的 Result 列。
- **不要只看 PDF 畫面**；規則對的是文字座標／排版字串（OCR 時為 OCR 字串）。
- **只抽 Result 有的欄位（使用者 2026-09-29）**：不在 `InvoiceExtract_Result.xlsx` 的欄位一律不抽、不驗。Result＝Summary（Invoice No.／Packages／Package Mode／G.W.／Incoterms／Invoice Value／LINE／QTY／Invoice Currency／**BL No.／BL Packages／BL G.W.**）＋ Lines（PN／Des／Qty／Unt／Amt／UoM／Co／HS code／N.W.／InvoiceNumber／Currency）；提單只抽 **BL No.／BL Packages／BL G.W.**（船名、航次、ETA／ETD、CBM、港口、櫃號、發票參照都不抽；只用來分類或交叉驗證件數／毛重可以，但不輸出）。新增欄位前先確認 Result 有該欄。自 MA 3rd 的 `cosco_arrival_v1`／`kwe_sea_waybill_v1` 起適用；既有已審的舊提單格式不回改。

### 3. 定錨點（分類）

- 寫 `MATCH_HINTS`＋`match_score`：廠商名、發票號型態、獨特標題（如 `Ladeliste`、`Net invoiced value of goods`）。
- 檔名與內文加減分；明顯是他家的關鍵字要扣分，避免誤吃。

### 4. 寫 Summary／header 規則

- Invoice No、標籤總額（如 `Final amount`、`Net invoiced value of goods`）、GW（**Gross 不是 Net**）、Packages、Incoterm、Currency 等。
- 金額優先錨在「標籤總額」，不要誤用單價列。

### 5. 寫 Lines／明細規則

- 欄位對齊匯出：`PN`／`Des`／`Qty`／`Unt`／`Amt`／`UoM`／`Co`／`HS code`／`N.W.`／`InvoiceNumber`／`Currency`。
- 與 packing／序號／裝箱列分開，避免把包裝列當商業明細。

### 6. 硬校驗（防假 pass）

- 有標籤總額時：`header.amount` 與 `sum(Lines)` 都必須對上該標籤（容差內），否則 **fail**。
- LINE／QTY 與明細列數／數量一致；自洽但錯的抽出（例如只抓 1 行單價）不得判 pass。

### 7. 登記種子（seed）＋版次

- 新增／更新 Python 模組，並掛進 `rules_engine.BUILTIN`。
- 跑種子把該版寫入 DB（新廠商或新 `version`）；**禁止為了圖方便覆寫舊 version 的語意**。
- 大改版 → 新 `format_id`（`*_v2`）＋新 DB version，舊票仍可對舊規則。

### 8. 跑樣本驗收

- 看 Excel：`Summary` 一列／`Lines` 明細；對人眼與文字層。
- 依 **AuditSOP**：產出 JSON **與 invoice 頁面圖** 給 Auditor（圖文對照）；**硬校驗 pass ≠ 最終收件**，人／Auditor 點頭才算。

### 9. 寫進文件

- 在本 FormatSOP 或模組 `NOTES` 註記：錨點、已知陷阱、對應 VBA Sub 名稱、樣本檔名。

### 10. （可選）發 portable

- 日常可只推 `main`。要給同事免安裝包時再打 Windows portable（內建 poppler／範本）。

---

## 現有 format 速查（錨點印象）

| format_id | 主要錨點（摘要） |
|-----------|------------------|
| `pt_gloria_v1` | `Robert Bosch Power Tools GmbH`、`Invoice No.`、`Net invoiced value of goods`；對齊 VBA `PT_PDFextract`／`PT_Declaration`；pkg＝Shipping unit 數 → 無則 Packing `total : N` → 類型加總（含 Bosch-Standard-Palette／Palette／Slip sheet）；無 Shipping unit 且 packing 列數≠`total : N` → total_pkg **needs_gold**（`meta.needs_gold_fields`，值＝建議值）；`labeled_amount`＝Net invoiced value of goods（後備 `Value:`）；soft note：HS 位數混用 |
| `pt_dremel_head3_v1` | Tool Corp Dremel head3：`Invoice No:`、`Origin/Tariff Code`、`Total:`；VBA `PT_PDFextractDremel_head3`／`PT_Dremel_Declaration_head3`；GW soft-missing OK |
| `pt_dremel_head5_v1` | Tool Corp Dremel head5：`Bosch Document Number`、`Value of Goods`、`Country of Origin`+`HSN/SAC`；VBA `…_head5`；GW＝packing Totals Gross |
| `bitzer_v1` | `BITZER`、`Ladeliste`、`Commercial Invoice`、`Final amount` |
| `nidec_v1` | `NIDEC TECHNO MOTOR`、`Invoice No. VKT…` |
| `hangji_v1` | Hangji／`GDHJ-…` |
| `hitachi_gls_v1` | Hitachi GLS／`MEH…`；兩種版面：表格明細（MEH6A036）與 `ITEM#` 內嵌配件版（MEH6J044：PN＝機型 PC-ALHZ1…、品名取下一行 `ACCESSORY:`、各機型產地取 `-ORIGIN:` 行）；金額＝標籤 GRAND TOTAL；packing TOTAL 支援千分位逗號；抽不到明細 → needs_gold（不再 0 行假 pass）；Incoterm `F.O.B. SHIMIZU, JAPAN` |
| `highly_v1` | HIGHLY／海立、`INV#` |
| `ma_no_period_v1` | `Robert BOSCH GmbH`、`Document No.`、`Goods Value`、13-char 無點 PN；VBA `MA_PDFextract_NoPeriod`／`MA_Declaration_noPeriod`；產地＝`Right(PN,3)`→**Country Of Origin Index**（可跨頁／首頁僅標題；勿用 `Country Of Origin\\b` 當結尾以免吃到下一頁 Index；Unicode 國名如 Türkiye） |
| `ma_with_period_v1` | 同上但 PN 有點（`0.445…`）；VBA `MA_PDFextractWithPeriod`／`MA_Declaration_withPeriod`；資料夾 90-C*／90-M* |
| `ma_ak_billing_v1` | `Billing Document AK…`、`Bosch Material No.`、`Commodity Code`、`Country of Origin`；VBA 無對應（新 AK 帳單）；pkg/GW＝Marking HU／Dummy Pack；**非** Document No./Goods Value／Origin Index |
| `bhc_my_hub_v1` | `Bosch Home Comfort Supply`、`TOTALS:`、`PART NO`；packing／GW soft-missing OK |
| `hisense_qingdao_v1` | `QINGDAO HISENSE BOSCH`、`CI NO.: CIHT-TW-…`、合訂 INV+PL；PN＝SELLER'S MODEL |
| `aichi_electric_v1` | `AICHI ELECTRIC`、`AETW…`、`Total FOB Nagoya`、合訂 packing sheet；PN＝DWG No. |
| `shanghai_nature_v1` | `SHANGHAI NATURE`、`NBT…`、`HEATING BELT`；OCR 掃描件 OK（case7） |
| `marubeni_tetsugen_v1` | `MARUBENI TETSUGEN`、`JCH##-##M#`、`COPPER TUBE`／`FOB NAGOYA`；OCR OK（case2） |
| `soe_rb_gmbh_v1` | SOE `Robert Bosch GmbH`、`Bosch Partnumber`、`Invoice Copy`／`Invoice and Packing List`、`Invoice amount`、`Total gross weight`、`Customs tariff no`；70775…／70918…；OCR OK（掃描 cargo list＋DN＋invoice 合檔；OCR PN 對帳：品項列／Customer PN／cargo list／transport order 各讀法，字形相似類須佔全部讀法過半；類內逐位：G/6 → G（即使少數）、其他（0/O、1/I、5/S、2/Z、8/B）取該位過半者，平手 → `needs_gold_fields=[items.part_no]`）；無 Total gross weight → Marking `N Pallets` 下 Gross weight；`N cardboard pallet` 亦計 pkg；向量字型薄文字層 → rules_engine OCR 重試 |
| `suzhou_aichi_v1` | `SUZHOU AICHI TECHNOLOGY`、`SATJG…`、ROTOR／STATOR 列（PN 可能在下一行 `AE75D1SC(2NE34604D)`）；金額＝標籤 TOTAL（OCR 只錯首位數字時接受 sum(lines)＋附註）；pkg＝`TOTAL: N Plywood Pallets`、GW＝PL TOTAL 第 2 個重量（Gross，非 Net）；Incoterm 照頁面讀（不再預設 FOB SHENZHEN）；OCR OK（BHC 3rd case1、4th case2；≠ `aichi_electric_v1`） |
| `sumitronics_hk_v1` | `SUMITRONICS`、`ST########`、PCB ASSEMBLY、FOB HAIPHONG；xlsx twin OK |
| `dunan_v1` | `ZHEJIANG DUNAN`／盾安、`DA…` slash INV nos、FOB NINGBO；xlsx OK |
| `ohizumi_dongguan_v1` | `DONG GUAN OHIZUMI`／东莞大泉、`OHIZUMI-…OUT`、TEMPERATURE SENSOR；xls OK |
| `oukai_v1` | `Changzhou Oukai`／欧凯、`OK########`、Step Motor；xls primary |
| `hitachi_asia_hitt_v1` | `Hitachi Asia Ltd`、`USDI…`、HITT NO／BHC NO；≠ `hitachi_gls_v1` (MEH) |
| `bhc_manual_inv_v1` | `TW-MANUAL-…`、no commercial value；≠ MY-HUB `TOTALS:` table |
| `bhc_vendor_ci_v1` | **BHC 小廠 CI 版面家族（一個 format_id，多個 vendor profile，`meta.notes` 記 `profile=`）**：`sanhua`（浙江三花 `SHC/THT…`，PDF＋xls twin；PN＝CUSTOMERS NO.，PDF 空白時 PN 留空＋附註）、`welling`（WELLING `MDBWH…`，`CI PL` 合訂；產地未印 → Co 空白＋附註）、`broad_ocean`（大洋 `…-BHC-TW` xls＋分檔 PL xls）、`hipus`（HIPUS `###-BHCTW-##K-##`，PDF＋xlsx twin（Header／Detail sheet，靠發票號錨點認）；一份 PL 給兩張 INV）、`hailiang`（海亮 `##HLHK…` xlsx，銅材以 KG 計，PN＝PO NO）、`katata`（KATATA `BSTW…`，PDF OCR＋xlsx twin；PN＝MODEL NO.）、`nisshinbo`（日清紡 `TAWA-…`，OCR 合訂 INV+PL；PN＝`2GF…`；HS 未印＝soft）；有 `parse_packing(text)` 給分檔 PKL 用（見下）；遇到提單／到貨通知字樣扣分 |

**MA**：WithPeriod／NoPeriod 已進規則庫（Round4）。其他變體（USA／Wiper／Sebang）尚未做。  
**MA 3rd（最後一批 MA）**：RBDEsea `90-C-26MA-*`（`INVOICE 2120xxxxxx.PDF`）＝`ma_with_period_v1`（HS 8 位＝發票印的 `HS CODE`）；RBJPsea `90-KWE-26MA-*`（`00…_2000…_RBTW_….PDF`）＝`ma_no_period_v1`（HS 10 位）。兩者規則**未改**，原樣 184/184 硬校 pass。RB 唯一鍵本批皆單段（DE 9 位、JP 13 位 `9843…001`），無兩段接合案例。**跨發票同一 RB（使用者 2026-09-29）**：MA 同一 shipment（同資料夾＋同 BL No.）有多張 INV、且 RB 唯一鍵在發票間重複時，件數／毛重以 **shipment 整體**計（RB 只算一次），依發票號碼排序全部放在**第一張**，其他各張件數／毛重＝0；品項行 qty／金額不動；各張都在 Summary 的 Packages／G.W. 儲存格加 Excel 附註（並寫 `meta.notes`、`header.summary_note`、`meta.shipment_packing`），其他張如「shipment pkg/GW (deduped) on 2120394532; printed pkg/GW 26 / 1989.836」，第一張如「shipment pkg/GW (deduped) 26 / 1989.836 on this first invoice (2 invoices, shared RB 110936597); printed pkg/GW 1 / 11.604」。**沒有 RB 重複的 shipment 不動**（各張照印刷值）。例：008 → 2120394532＝26／1989.836、2120394533＝0；036 → 2120422517＝32／2801.031、2120422518／2120422519＝0（皆＝BL，差 ≤0.002 為四捨五入）。實作：格式把包裝單位放 `meta.packing_units`（MA＝RB 鍵→毛重），`pairing.dedupe_shared_packing_units` 於整批抽完後執行（CLI／GUI），`SHARED_RB_MODE="shipment_first"`（另保留 `duplicate_only` 僅供對照，不用）；若某 INV 的件數／毛重不是由這些單位算出（例 PKL 覆寫）→ 不搬移，整個 shipment 標 `total_pkg`／`gross_weight_kg` needs_gold。

---


## INV／PKL 分檔與 format_id

合訂本（同一 PDF 含發票＋packing）與 **分檔**（常見於 **BHC**：`*_INV_*` + `*_PKL_*`）共用同一套 FormatSOP：主 `format_id` 仍由 **INV（或合訂本）** 的 `match_score` 決定，**不**另開 `*_pkl_v1` 當主類別。分檔時 PKL 只當**同家族補充來源**（件數／GW：MA 用 `parse_rb_packages`；BITZER／通用 packing 錨點亦可），合併成一筆 ExtractResult；`meta.source=combined|split`。MA 多數仍為合訂本，勿假設全部都要分檔。

**BHC 4th／5th Auditor 複審修正（2026-10-05）— 印得清楚的提單值不可留 needs_gold**：
- 共用 OCR 工具 `ocr_reread.py`：`page_words`（一次 OCR 拿字框，可先 `remove_hlines` 去掉 1–2 px 橫向底紋）＋`reread_clip`（只把定位到的那個值用單行模式 `--psm 7`＋字元白名單，在多個解析度重讀；每個解析度算一個讀法，跟整頁讀法一起投票）。只用 pymupdf＋tesseract（portable 不需 numpy／PIL）。
- **`tvl_hbl_v1`**：根因＝200 dpi 細線二值掃描整頁 OCR 會換掉單一字形（3185→3488／3485、1195.5→1498.5、269→268），第二次 300 dpi 整頁又讀不到 → 只剩一個錯讀法被當建議值。修法：200 dpi 找表面重量字（`…KGS`）與 B/L No.（`SHAKEL…`／`QDEX…`）的位置，各重讀 200／300／400 dpi；表面**只有一個**重量字時才用（多櫃明細照舊用列加總投票）；重讀一致（≥2 且過半）時 slash 列的整頁讀法也讓位。BL No. 讀法含重讀過半 → 不標 needs_gold。
- **`jif_cosmo_waybill_v1`**：根因＝防偽底紋是細橫線，整頁只讀到 `998, 000`（掉千位）或讀不到，又只有一次 OCR → GW 永遠 ≤1 讀法。修法：300 dpi 去底紋（垂直 opening k=3）再整頁 OCR 一次（件數 `N PALLETS (… PIECES)`／`CONTAINER<N PALLETS` 也多一組讀法），再把重量重讀 300／400／600 dpi。投票門檻不變（≥2 一致且過半）。
- 結果：4th case1 8／3185、case6 16／1998、case8 10／3084.5、5th case1 6／1195.5 皆不再 needs_gold；舊批 BHC 2nd case7 `SHAKEL26970898` 1／231（原審 gold）GW 旗標也解除。每份掃描提單多 2–3 秒。

**BHC 5th 新增（2026-10-05）**：
- **`bhc_vendor_ci_v1` profiles**：`katata`（KATATA ELECTRIC `BSTW…`，PDF OCR＋xlsx twin；PN＝MODEL NO.；`PACKING : N PALLET`／`Gross Weight`）、`nisshinbo`（NISSHINBO `TAWA-…`，OCR 合訂 INV+PL；PN＝`2GF…`；pkg＝CTNS；HS 未印＝soft）。
- **`tvl_hbl_v1`**：SAY OCR（`$1X`→SIX、SAYTOTAL、em-dash）、marks `C/NO.…/N PALLET`、slash-row GW 優先（件數一致時）、多 pass 未印證的 GW → needs_gold。
- **`nidec_v1`**：BILL OF LADING／SHAKEL／T.V.L 扣分（避免掃描提單被當發票）。

**BHC 4th 新增（2026-10-05）**：
- **廠商專用 PKL 解析**：INV 的 format 模組若有 `parse_packing(text)`（目前 `bhc_vendor_ci_v1`），分檔 PKL 的件數／毛重先用它，抓不到才退回通用 `parse_packing_pkg_gw`；`meta.notes` 記 `pkl_parser=<format_id>`。例：大洋 PL 通用解析誤抓 2352（pcs），專用解析＝7 板／1876 kg。
- **一份 PL 對多張 INV**：PKL 檔名同時含同資料夾 ≥2 張 INV 的編號（例 `PL_117-BHCTW-26K-41, 121-BHCTW-26K-37.xlsx`）→ 這份 PL 配給每一張 INV（含 xlsx twin），每板當一個包裝單位（`meta.packing_units`），再用 MA 的 `shipment_first` 規則：shipment 總件數／毛重放第一張（發票號排序；同發票號的 PDF／xlsx twin 都算第一張），其他張 0＋Summary 附註。**使用者 2026-10-05 確認：BHC 共用 PL 也用 `shipment_first`（第一張放整批件數毛重，其餘 0＋附註），為 BHC 通用規則。**
- **同一提單多份副本**：同資料夾 ≥2 個提單檔且 BL No. 相同（例 `WAYBILL.pdf`＋掃描 `20260921195744-0001.pdf`）→ 只用讀得最完整的一份（件數／毛重有值的多、needs_gold 欄少），其他副本記在 `meta.notes`「duplicate BL copy … not used」，不另出 僅提單 列。
- **檔名 `CI` = Commercial Invoice**（`CI PL MDBWH….pdf` → 合訂本）。

## 完成定義（Definition of done）

- [ ] 樣本抽出 Summary／Lines 正確（含 GW＝Gross、金額＝標籤總額）
- [ ] 假抽出（少行／誤單價）硬校驗會 fail
- [ ] 模組已掛 `BUILTIN`；DB 已種子登記且未覆蓋舊版語意
- [ ] NOTES／本 SOP 有錨點與陷阱說明
- [ ] （若要給現場）portable 另開任務打包

---

## 修訂紀錄

| 日期 | 說明 |
|------|------|
| 2026-10-05 | BHC 4th／5th Auditor 複審修正：新 `ocr_reread.py`（字框定位＋單行多解析度重讀＋去橫向底紋）；`tvl_hbl_v1` 表面單一重量字與 B/L No. 重讀投票（4th case1 3488→3185、5th case1 1498.5→1195.5）；`jif_cosmo_waybill_v1` 去底紋第二次 OCR＋重量重讀（4th case6 GW 空白→1998、case8 needs_gold 解除）；BHC 共用 PL `shipment_first` 經使用者確認 |
| 2026-10-05 | BHC 5th（3 case；.msg 忽略）：`bhc_vendor_ci_v1` 加 profile `katata`（BSTW OCR＋xlsx twin）／`nisshinbo`（TAWA OCR 合訂）；`nidec_v1` 沿用 VKT26075（提單文字扣分，避免吃 TVL HBL）；`tvl_hbl_v1` SAY OCR 強化（`$1X`→SIX、SAYTOTAL、em-dash、`C/NO.…/N PALLET` marks）、slash-row GW 在件數對得上時優先（13101 vs face 13104）、多 pass 無第二讀法的 GW → needs_gold（case1 圖上 1195.5、OCR 誤 1498.5）；review `docs/review_shots/bhc_5th/` |
| 2026-10-05 | BHC 4th（11 case；.msg 忽略）：新 INV 家族 `bhc_vendor_ci_v1`（profile sanhua／welling／broad_ocean／hipus／hailiang＋`parse_packing`）；擴充 `suzhou_aichi_v1`（STATOR+ROTOR、標籤 TOTAL、Gross GW、Incoterm 照頁面）、`hitachi_gls_v1`（MEH6J044 內嵌配件版、GRAND TOTAL、0 行 → needs_gold）；新 BL `jif_cosmo_waybill_v1`（JIFFA／Cosmo Trans Line waybill，防偽底紋 OCR，≥2 讀法一致才採用）；`tvl_hbl_v1` 掃描件跑第二次 OCR（300 dpi）投票：櫃別明細加總（需等於表面總重）、SAY TOTAL 英文＋括號數字（排除櫃數）、表面件數（`(` 誤讀成 `1` 修正）；BL No. 兩次讀法不同 → needs_gold（GW 只有一個讀法時一起標）；QDEX 提單號；圖片輸入（jpg／tif）；空白 Excel 範本略過；配對：`CI` token、一份 PL 對多張 INV、同提單多副本、廠商專用 PKL 解析、twin 列在 shipment_first 都算第一張；review `docs/review_shots/bhc_4th/` |
| 2026-09-29 | MA 3rd **Round 2**（Auditor：INV 184/184、DE BL 19/19 pass；JP BL 核心欄 20/20 正確）：新規則「只抽 `InvoiceExtract_Result` 有的欄位」——`cosco_arrival_v1`／`kwe_sea_waybill_v1` 只輸出 BL No.／BL Packages／BL G.W.，移除船名／航次／ETA／ETD／CBM 等（含原 Round 2 的 ETD／CBM 修正），舊提單格式不動；`BLMeta.needs_gold_fields`（逐欄帶到 INV 列）；亂碼文字層 OCR 經 Auditor 核准：判準不放寬、backend 加 `+mojibake_layer` 並記錄、用語改「OCR when the text layer is empty or unreliable」；跨發票同一 RB（008／036）：shipment 整體去重後的件數／毛重放第一張（發票號排序）、其他張 0＋Summary 附註（`dedupe_shared_packing_units`，mode B `shipment_first`） |
| 2026-09-27 | MA 3rd（最後一批 MA；39 資料夾（RBDEsea 19＋RBJPsea 20）／223 PDF：184 INV＋39 提單＋0 缺 BL）：INV 沿用 `ma_with_period_v1`（RBDEsea 90-C）／`ma_no_period_v1`（RBJPsea 90-KWE），未改規則；新 BL family `cosco_arrival_v1`（COSCO 到貨通知，文字層）＋`kwe_sea_waybill_v1`（KWE／APL SEA WAYBILL 掃描，OCR 投票：件數／毛重需 ≥2 讀法一致且過半，否則 needs_gold）；`looks_like_bl_filename` 認 `BL##########`；`text_layer_looks_mojibake`（影印機中文 OCR 疊在英文頁的亂碼層 → 視同不可靠，改 OCR）；提單 needs_gold 會帶到 INV 列（`needs_gold_fields` += `bl_*`）；配對時同一提單只抽一次（快取）；review `docs/review_shots/ma_3rd/` |
| 2026-09-26 | SOE 2nd **Round 2b**（Auditor 15/15 pass＋規則風險）：字母優先只限 G/6；其他字形相似對逐位嚴格過半（數字或字母），平手 → needs_gold；真數字尾碼（-2U1、-501）不再被翻成字母 |
| 2026-09-26 | SOE 2nd **Round 2**（Auditor 13 pass／2 conflict）：`soe_rb_gmbh_v1` OCR PN 對帳取代「尾碼不一即 needs_gold」：候選＝品項列點號 PN、Customer PN 無點形、cargo list／transport order／DN 料號欄（數值標籤欄如 `Volume in cdm` 排除）；字形相似類過半 → 字母形（7369301、7405713 → `-57G`；1267475174 保持 `-57G`）；無過半 → needs_gold；分隔符誤讀且無第二讀法 → needs_gold |
| 2026-09-26 | SOE 2nd（**只跑 invoice**，15 份／13 case，全 `soe_rb_gmbh_v1` 擴充，無新 format_id；HBL／PL／XC PL xlsx／NCN93230104 NEC HAWB 跳過）：OCR PN 分隔符修補（純空白＝良性；`,` 代 `.`＝字形誤讀 → needs_gold）、OCR 同 PN 尾碼多讀法（57G／576）→ `items.part_no` needs_gold；Marking GW fallback；裸原產地行；`N cardboard pallet`；缺頁 soft note；`rules_engine` 薄文字層（<400 字/頁、≤10 頁）且無 format 命中 → OCR 重試（`+thin_text_layer`）；review `docs/review_shots/soe_2nd/` |
| 2026-09-26 | PT 4th **Round 2**（Auditor 22 pass／1 needs_gold）：`pt_gloria_v1` 無 Shipping unit 且 packing 列數≠`total : N` → `needs_gold_fields=[total_pkg]`（checker 其餘硬校仍跑，過則 verdict＝needs_gold）；`labeled_amount` 由 NIV／`Value:` 填入，硬校比對標籤總額 |
| 2026-09-26 | PT 4th（23 PDF／15 case，全 `pt_gloria_v1` 擴充，無新 format_id）：無 Shipping unit 時 pkg 取 Packing `total : N`；packing 詞彙＋`Bosch-Standard-Palette`／`Palette`／`Slip sheet`；soft `meta.notes`（50663231 列 1 vs total 12；50664217 HS 8/10 位混用）；review `docs/review_shots/pt_4th/` |
| 2026-09-24 | BHC 3rd **Round 3**：`tvl_hbl_v1` CBM from CARTONS/KGS/CBM + 20GP≤33; ISO container+seal; all BHCWH* refs; GO.→CO. OCR
| 2026-09-24 | BHC 3rd **Round 2**：`tvl_hbl_v1` prefer CARTONS over Say-Total 20GP + GW OCR cross-check (.830→.53 / mistrust mismatched CARTONS/KGS); PKL overlay uses `extract_text` + stale-layer→OCR (`text_layer_looks_unreliable`); QA/Hitachi PKL pkg/GW parsers; `oukai_v1` soft note when vendor Total qty ≠ sum(lines)
| 2026-09-24 | BHC 3rd batch (cases 1–9)：`suzhou_aichi_v1`／`sumitronics_hk_v1`／`dunan_v1`／`ohizumi_dongguan_v1`／`oukai_v1`／`hitachi_asia_hitt_v1`／`bhc_manual_inv_v1`＋BL `hippopo_arrival_v1`／`dhl_danmar_bl_v1`／`china_progress_bl_v1`；`.xls` via xlrd；review `docs/review_shots/bhc_3rd/` |
| 2026-09-24 | GUI／CLI 接受 Excel 輸入；Excel format 仍走 FormatSOP（cell→text） |
| 2026-09-10 | 初版：與使用者復盤後定稿；澄清種子與 v1／v2 選法 |
| 2026-09-13 | 分檔 PKL 為同家族補充來源（BHC 為主）；主 format_id 看 INV／合訂本 |
| 2026-09-13 | BHC cases 1/3/6/8：`hisense_qingdao_v1`／`aichi_electric_v1`；MY-HUB 連字號 PN＋分檔 PKL TOTAL
| 2026-09-13 | MA NP：硬化 `_parse_coo_index`（空 Index 頁＋跨頁＋Unicode Türkiye）；WP 不變 |
| 2026-09-10 | Round4：種子 `ma_no_period_v1`／`ma_with_period_v1`／`bhc_my_hub_v1` |
| 2026-09-15 | MA inv+bl 6：`milestone_arrival_v1`（里運／Milestone）；同資料夾 N INV↔1 BL 共用 Summary BL 欄 |
| 2026-09-20 | MA new sample：`ma_ak_billing_v1`（Invoice AK…）＋`nippon_express_awb_v1`（pdfdq NEM AWB）；milestone 沿用 90-S HBL；OCR sidecar 支援掃描到貨 |
| 2026-09-15 | PT Dremel：`pt_dremel_head3_v1`／`pt_dremel_head5_v1`（vs Gloria；16 PDF；HS hard；head5 GW=Gross） |
| 2026-09-23 | MA-747 90-S：FWD+SAP AK Billing（byte-identical）+ milestone HBL005289；`ma_ak_billing_v1` FWD `AK…_INV` score；hard_check 0.1% line relative tol（Net Value≠Unit×Qty） |
| 2026-09-21 | SOE 1st：`soe_rb_gmbh_v1`＋`kwe_air_waybill_v1`／`maersk_air_waybill_v1`；PT round3 既有 gloria／dremel head5 全過；BHC 罰 INV_PL_/Bosch Partnumber |


---

## BL / 到貨通知 / HBL（平行路徑）

發票 FormatSOP 仍適用「收樣本→文字層→錨點→抽欄→硬校→種子→驗收」。BL 差異：

| 項目 | BL |
|------|-----|
| 模組位置 | `src/invoice_extractor/formats/bl/<id>.py` |
| 引擎 | `bl_rules_engine.BUILTIN_BL` / `extract_bl` |
| Schema | `schema_bl.BLExtractResult`（`doc_type: bl`） |
| 硬校驗 | `checker_bl.hard_check_bl`（需 bl/hbl + ≥1 of pkg/GW/ETA） |
| CLI | `--doc-type bl` → Excel **`BL`** sheet；發票模式配對後寫入 Summary BL 三欄 |
| 種子 | `--init-db` 一併寫入 BL vendors |

### 現有 BL format 速查

| format_id | 主要錨點 |
|-----------|----------|
| `ceva_pyramid_arrival_v1` | `到貨通知`、`CEVA LOGISTICS`、`PYRAMID LINES`、`B/L no`（case4/5/6 共用） |
| `dhl_lcl_arrival_v1` | `海運 LCL 到貨通知`、`HBL 提單號碼`、`DHL GLOBAL FORWARDING` |
| `hippopo_hbl_v1` | `HIPPOPO`、`HB########`、HBL draft 稀疏欄位 |
| `tvl_hbl_v1` | `T.V.L. GLOBAL LOGISTICS`／`TRANS VAN LINKS`、`SHAKEL…`／青島 `QDEX#######` HBL（OCR OK）；BHC 4th 起掃描件做第二次 OCR 投票：件數讀法＝SAY TOTAL 英文＋括號數字（`SAY TOTAL: ONE (1) 20'GP…CONTAINERS` 不算件數）、櫃別明細 `N PACKAGES/CARTONS/PALLETS / X KGS` 加總（僅當重量和＝表面總重）、表面件數（`190 CARTON`＝`(90`）；毛重讀法＝表面 3 位小數 KGS、明細重量和；≥2 一致且過半才改值，舊批沒有讀法時照舊；BL No. 兩次讀法不同（且檔名無法決定）→ needs_gold |
| `milestone_arrival_v1` | `MILESTONE FORWARDING`／`里運國際`、`ARRIVAL NOTICE 到貨通知書`、`B/L NO : HBL00#####`（MA 90-S 六包共用） |
| `nippon_express_awb_v1` | `AIR WAYBILL`、`NIPPON EXPRESS`、`NEM #### ####`（MA 50-N pdfdq 空運提單） |
| `kwe_air_waybill_v1` | `KINTETSU WORLD EXPRESS`、`Air Waybill`、`1220-########`（SOE HAWC） |
| `maersk_air_waybill_v1` | `MAERSK LOGISTICS`、`HAWB No: QU########`（SOE HAWB） |
| `hippopo_arrival_v1` | Hippopo **到貨通知書**、`B/L NO :` CPSE／P076…（≠ HBL draft `hippopo_hbl_v1`） |
| `dhl_danmar_bl_v1` | `Danmar Lines`／DHL GF Japan ocean B/L、`NGOA…`（≠ `dhl_lcl_arrival_v1`） |
| `china_progress_bl_v1` | `CHINA PROGRESS`／中进国际、`NBSE…` 提单 |
| `cosco_arrival_v1` | COSCO SHIPPING（中國遠洋）`到貨通知`／`ARRIVAL NOTICE`、`B/L Number: COSU##########`、檔名 `BL##########.PDF`；**只輸出 Result 欄**：BL No.＝`COSU…`、件數／毛重＝附頁 `Total: N … X KG`（與首頁櫃列 箱型/毛重/總件數 交叉比對，不一 → needs_gold）；不抽船名／航次／ETA／港口／櫃號／CBM／發票參照；MA 3rd RBDEsea 90-C |
| `kwe_sea_waybill_v1` | KWE／APL Logistics `SEA WAYBILL NON-NEGOTIABLE`、`WAYBILL NO. 1220########`（12 位；≠ 空運 `kwe_air_waybill_v1`）；掃描件 → OCR；**只輸出 Result 欄**（BL No.／件數／毛重）；件數讀法：`N SAID TO CONTAIN`、內文 `N PACKAGES`、`(P PALLETS(=C CARTONS), L CARTONS)`、`(N) PACKAGES ONLY`、第 2 頁 `N PCS`；毛重：`SAID TO CONTAIN: X`、TOTAL 列、第 2 頁 `X KG`；≥2 一致且過半才採用，否則 needs_gold（保留建議值）；BL `meta.needs_gold_fields` 逐欄帶到 INV 列（`bl_<欄>`）；不抽船名／航次／ETD／港口／CBM／發票參照；MA 3rd RBJPsea 90-KWE |
| `jif_cosmo_waybill_v1` | Japan International Freight Forwarders（JIFFA 表單）／`COSMO TRANS LINE` waybill、`######KEE###`（OCR 空格去掉）；防偽底紋 → OCR 雜訊大；**只輸出 Result 欄**；件數讀法：`N PALLETS (… PIECES)`、`CONTAINER<N PALLETS`、附頁最後一個 `CASE NO. N`；毛重：`SAID TO CONTAIN` 下一行 `x,xxx.xxx`（後面的是 M3）；≥2 一致且過半才採用，否則 needs_gold（保留建議值；讀不完整如 `998, 000` 只記在 notes）；BHC 4th case 6（260918KEE103）、case 8（260918KEE102） |

**掃描提單文字層**：文字層空 → OCR（照舊）。文字層非空但為影印機「中文 OCR 疊在英文頁」的亂碼（`BOSCH CORPORA下 工ON`、`SH︳ PPER`）→ `text_layer_looks_mojibake` 判不可靠，改用 Tesseract（backend `ocr/tesseract+prefer_over_stale_layer+mojibake_layer`；CLI 警告「PDF text layer is unreliable (garbled scanner CJK-mode OCR…)」＋ log 記錄實際 backend）。**Auditor 2026-09-29 核准**此例外，條件：判準維持目前的窄度（不得放寬門檻）、記錄 OCR backend、SOP 用語改為「OCR when the text layer is empty or unreliable」；判準：CJK 類字元 ≥200、其中 ≥45% 緊貼英數、直排／框線／全形括號類 ≥3%（COSCO 到貨通知≈7% 貼英數、Hangji 發票≈37%、MA Label≈0 CJK，皆不觸發）。

**Multi-INV same BL（同資料夾）**：一張到貨通知對多張 INV（例 548／616）時，每個 INV Summary 列都帶同一組 `BL No.`／`BL Packages`／`BL G.W.`（不覆寫發票 Packages／G.W.）。

GUI 配對欄：`配對 | INV | PKL | 提單 | 狀態`；Summary 三欄由 pairing merge 填入。

