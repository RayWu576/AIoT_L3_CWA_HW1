# 📋 專案實作工作流與執行計畫 (Workflow & Implementation Plan)

> **專案名稱**：AI 創新微課程：Taiwan Weather Forecast (台灣互動式天氣預報)  
> **專案儲存庫**：[RayWu576/AIoT_L3_CWA_HW1](https://github.com/RayWu576/AIoT_L3_CWA_HW1)  
> **核心技術棧**：`CWA API` × `JSON` × `Python` × `Pandas` × `SQLite` × `Streamlit` × `Folium` × `GitHub`

---

## 🗺️ 工作流全景圖

![Workflow 全景學習地圖](../assets/workflow.jpg)

---

## 🎯 專案目標與願景
建立一套完整的端到端（End-to-End）氣象數據應用系統：
1. **自動化擷取**：透過中央氣象署 (CWA) Open Data API 取得一週全台分區氣溫預報。
2. **結構化儲存**：解析多層 JSON 資料，清洗並存入本地輕量級 SQLite 資料庫 (`data.db`)。
3. **互動式儀表板**：使用 Streamlit 打造無伺服器負擔的 Web App，支援分區切換、一週溫差趨勢折線圖與明細清單。
4. **地理空間視覺化**：整合 Folium 地圖，依據氣溫高低動態呈現分區溫標顏色。
5. **軟體工程品質**：實作防重複插入 (Idempotency)、錯誤容錯機制 (Exception Handling) 與 Git 版本控制。

---

## 🏗️ 系統架構與檔案規劃

```text
AIoT_L3_CWA_HW1/
│
├── .gitignore               # Git 忽略設定（忽略虛擬環境、暫存檔與快取）
├── README.md                # 專案總覽說明文件
├── requirements.txt         # 專案相依套件清單
│
├── assets/                  # 專案靜態資源
│   └── workflow.jpg         # 課程與實作全景流程圖
│
├── myplan/                  # 專案計畫與工作流文件
│   └── workflow.md          # 詳細工作流與各階段實作計畫
│
├── src/                     # 核心程式碼
│   ├── config.py            # API 金鑰、資料庫路徑等常數配置
│   ├── cwa_api.py           # 串接 CWA API、取得與解析 JSON 資料模組
│   ├── database.py          # SQLite 資料庫建立、資料插入與查詢模組
│   └── app.py               # Streamlit + Folium 互動前端儀表板主程式
│
└── data/                    # 本地資料存放
    └── data.db              # SQLite 氣溫資料庫 (自動生成)
```

---

## 📝 24 步驟詳細執行任務清單 (Execution Checklist)

### 階段一：概念引導與環境準備 (Steps 01 ~ 03)
- [x] **01. 課程介紹**：確立學習目標、技術棧選型與預期成果。
- [x] **02. 台灣的天氣與生活**：理解氣象數據之民生價值與數據驅動決策概念。
- [x] **03. 中央氣象署 CWA 平台**：註冊帳號、取得專屬 `API Authorization Key` 並確認目標資料集代碼。

### 階段二：API 串接與資料解析處理 (Steps 04 ~ 07)
- [ ] **04. API 資料取得**：撰寫 Python `requests` 腳本，傳入 API Key 取得預報 JSON。
- [ ] **05. JSON 資料結構解析**：分析巢狀層級，定位 `locations`、分區名稱與氣象要素。
- [ ] **06. 提取最高與最低氣溫**：萃取 `MinT`（最低溫）與 `MaxT`（最高溫）之時間序列數據。
- [ ] **07. 資料整理與預覽**：使用 `pandas.DataFrame` 整理為二維表格，確認格式無誤。

### 階段三：資料庫架構設計與持久化 (Steps 08 ~ 10)
- [ ] **08. 建立 SQLite 資料庫**：透過 `sqlite3` 建立本地 `data.db`。
- [ ] **09. 資料表結構設計**：建立 `TemperatureForecasts` 資料表（包含主鍵、分區名稱、日期、最低溫、最高溫）。
- [ ] **10. 查詢資料驗證**：撰寫 SQL 查詢（如分區過濾、去重查詢）驗證入庫資料完整性。

### 階段四：互動式 Web 應用程式開發 (Steps 11 ~ 16)
- [ ] **11. Streamlit 入門**：安裝與建立基礎 Streamlit 應用架構。
- [ ] **12. 資料庫讀取串接**：利用 `pd.read_sql_query` 自 `data.db` 讀取即時數據。
- [ ] **13. 下拉選單選擇地區**：實作 `st.selectbox` 分區切換元件。
- [ ] **14. 繪製氣溫折線圖**：繪製一週高溫（MaxT 紅線）與低溫（MinT 藍線）動態走勢圖。
- [ ] **15. 顯示數據表格**：透過 `st.dataframe` 呈現結構化每日氣象明細。
- [ ] **16. Web App 介面整合**：優化網頁佈局（排版、標題、說明與響應式顯示）。

### 階段五：進階地圖視覺化與程式優化 (Steps 17 ~ 20)
- [ ] **17. 台灣地圖視覺化**：整合 `folium`，依據分區平均溫度顯示對應色階（藍/綠/橘/紅）。
- [ ] **18. 日期篩選與地圖聯動**：實作日期選擇器動態更新地圖標記與氣溫資訊。
- [ ] **19. 完整成果展示**：打造集指標卡片、圖表、地圖一體的 Taiwan Weather Dashboard。
- [ ] **20. 程式碼品質與優化**：模組化重構、例外處理（Try-Except）、防重複插入（Idempotency）。

### 階段六：版本管理與創新延伸 (Steps 21 ~ 24)
- [x] **21. 專案上傳至 GitHub**：初始化 Git 儲存庫並完成首次遠端同步。
- [ ] **22. 延伸應用構想**：評估 Line Bot 提醒、旅遊行程建議、農業防汛預警等加值應用。
- [ ] **23. 回顧與重點整理**：歸納 API 爬取、資料庫管理、Web 儀表板全端技能。
- [ ] **24. 下一步：持續探索**：結合更多開放資料 API 與 AI 輔助分析功能。

---

## 🗄️ 資料庫架構設計 (Database Schema)

```sql
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT NOT NULL,       -- 分區名稱 (如：北部地區、中部地區、南部地區等)
    dataDate TEXT NOT NULL,         -- 預報日期 (YYYY-MM-DD)
    minT REAL,                      -- 最低氣溫 (°C)
    maxT REAL,                      -- 最高氣溫 (°C)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(regionName, dataDate)    -- 防重複插入之唯一性約束 (Idempotent)
);
```

---

## 🌡️ 地圖溫標色彩標準 (Color Grading Rules)

| 平均溫度範圍 | 色彩標示 | 代表意涵 | 視覺色碼 |
| :--- | :---: | :--- | :--- |
| `< 20°C` | 🔵 藍色 | 偏冷 / 涼爽 | `#1E88E5` |
| `20°C ~ 25°C` | 🟢 綠色 | 舒適宜人 | `#43A047` |
| `25°C ~ 30°C` | 🟠 橘色 | 溫暖微熱 | `#FB8C00` |
| `> 30°C` | 🔴 紅色 | 炎熱高溫 | `#E53935` |
