# InvoiceExtractor — 混合架構（v0）

本地 portable 負責檔案／規則／庫；LLM 與檢查 Bot 當外掛。公司機能拷資料夾跑；沒網路也能用已學會的規則。

## 元件

```
[PDF / MSG / xlsx]
        │
        ▼
  ingest（文字層？→ layout text；否則標記 needs_ocr）
        │
        ▼
  classify（對 vendor_format 規則庫：檔名／關鍵字／樣本指紋）
        │
   有命中 ──► rules_engine（regex／欄位錨點）──► extract.json
        │                                              │
   未命中／低信心                                     ▼
        │                                    checker（硬校驗 + 可選 LLM）
        ▼                                              │
  llm_gold（API／Grok Bot）◄──── 不一致 ── 提案 patch（人按過才寫庫）
        │
        ▼
  人確認金標 → 從金標＋原文「編譯」新 format 規則 → 再跑 rules
        │
        ▼
  高信心 → 寫 inv_run 紀錄＋可選匯出 Excel
```

## JSON schema（兩版結果都用這份，檢查才比得了）

### header
- `invoice_no` string
- `invoice_date` YYYY-MM-DD | null
- `total_pkg` number | null
- `gross_weight_kg` number | null
- `incoterm` string | null
- `item_line_count` int | null
- `total_quantity` number | null
- `amount` number | null
- `currency` string | null
- `vendor` string | null

### item[]
- `invoice_no` string
- `part_no` 料號
- `description` 品名
- `qty` 數量
- `unit` 單位
- `unit_price` 單價
- `amount` 金額
- `origin` 產地
- `hs_code` 稅則
- `currency` 幣別

另附 `meta`: `source_file`, `text_backend`, `format_id`, `confidence` (`gold`|`rules`|`high`|`conflict`)

金額一律轉成小數（歐式 `6.052,400` → 6052.4）。缺欄位用 null，不要空字串混用。

## 規則庫 SQLite（`data/invoice_formats.db`，跟著 portable 資料夾走）

**vendors**：id, name, aliases

**formats**
- vendor_id
- version（整數，同一 vendor 可多條）
- status：active / deprecated
- match_hints：檔名 regex、正文關鍵字（如 BITZER、Ladeliste）
- rules_json：表頭／明細的 regex 與欄位映射
- notes、created_at

**runs**（每次匯入一張）
- source_hash, format_id, gold_json, rules_json_out, checker_verdict
- confidence, needs_human

比對不一致時：**新增 format version**，不覆蓋舊的（舊單才跑得回去）。

## 檢查 Bot（兩層，缺一層都不叫高信心）

1. **硬校驗（本地、必跑）**
   - `len(items) == item_line_count`（有填才比）
   - `sum(item.qty) ≈ total_quantity`
   - `sum(item.amount) ≈ header.amount`（容差 0.05）
   - 各 item.currency 與 header 一致
   - `unit_price * qty ≈ amount`（列級）
2. **語意檢查（可選 LLM）**：金標 vs 規則 JSON 的欄位 diff；只傳結構化 JSON＋原文摘錄，不傳整份 PDF。

Verdict：`pass` / `conflict` / `needs_gold`。conflict 產出「建議的 rules_json patch」，**預設要人按過**才寫入 formats。

## LLM 金標

- 輸入：layout 文字（可截前 N 頁＋含 Invoice／Total 的頁）
- 輸出：上面同一份 schema
- 失敗／無 API：標記 `needs_gold`，規則照跑但不標高信心

## Portable 範圍（第一版就做）

- CLI：`invoice-extract file.pdf ...` → 旁輸出 `.json`
- 本機 SQLite 規則庫
- layout text 復用現有 `pdf_layout_text`
- 硬校驗 checker
- 一個 `formats` 種子：BITZER／3000214469（你已對過）

**第一版刻意不做**：OCR、自動改 code、GUI 美化、純前端直連 LLM。

## 之後才接

- `--gold` 呼叫 API／Grok Bot
- 檢查 Bot 當獨立服務被 CLI 打
- 成功後開 Excel（沿用 PT 工具那套經驗）
