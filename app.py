import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path

# ── 路徑設定 ──
BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = BASE_DIR / "data" / "data.db"

# ── 讀取資料 ──
@st.cache_data
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT regionName, dataDate, minT, maxT "
        "FROM TemperatureForecasts "
        "ORDER BY regionName, dataDate",
        conn
    )
    conn.close()
    return df

# ── UI ──
st.title("Taiwan Weather Dashboard")
st.write("中央氣象署一週溫度預報")

df = load_data()

if df.empty:
    st.warning("⚠️ 尚無氣象資料，請先執行 `python fetch_data.py`")
    st.stop()

# M4-3：地區選擇
regions = sorted(df["regionName"].unique())
selected_region = st.selectbox("選擇地區", regions)

filtered_df = df[df["regionName"] == selected_region].copy()

# M4-4：一週高低溫折線圖
st.subheader(f"{selected_region} 一週溫度趨勢")
chart_df = filtered_df.set_index("dataDate")[["minT", "maxT"]]
st.line_chart(chart_df)

# 詳細資料表
st.subheader("詳細資料")
st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)
