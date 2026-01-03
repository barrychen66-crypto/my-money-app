import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import datetime

# --- 1. 設定區 ---
# ⚠️ 請將下方網址換成您自己的 Google 試算表網址！
SHEET_URL = "https://docs.google.com/spreadsheets/d/174jupio-yaY3ckuh6ca6I3UP0DAEn7ZFwI4ilNwm0FM/edit?gid=0#gid=0"

st.set_page_config(page_title="雲端記帳簿", layout="centered", page_icon="☁️")

# --- CSS 樣式注入：Gemini 選單風格 (淡藍底 + 深藍字) ---
st.markdown("""
    <style>
    /* 1. 整體背景：Gemini 風格的極淡灰藍色 */
    .stApp {
        background-color: #F0F4F9;
    }
    
    /* 2. 標題與一般文字：深灰色 */
    h1, h2, h3, .stMarkdown h3 {
        color: #1F1F1F !important;
        font-family: "Microsoft JhengHei", sans-serif;
        font-weight: 700 !important;
    }
    
    p, .stMarkdown p, .stMarkdown li, div {
        color: #444746 !important;
        font-size: 1.3rem !important;
        font-weight: 500;
    }
    
    /* 3. 輸入框標籤 */
    .stSelectbox label, .stDateInput label, .stNumberInput label, .stTextInput label, .stRadio label {
        font-size: 1.4rem !important;
        color: #444746 !important;
        font-weight: 700 !important;
    }
    
    /* 4. 按鈕：Gemini 風格 */
    div.stButton > button {
        background-color: #D3E3FD;
        color: #0B57D0 !important;
        border-radius: 24px;
        height: 4.5em; 
        font-size: 20px !important;
        font-weight: 800;
        border: none;
        box-shadow: none;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #C2E7FF;
        color: #004A77 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* 5. 分頁籤風格 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F0F4F9;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background-color: #E1E3E1;
        color: #444746;
        font-size: 20px;
        font-weight: 600;
        border-radius: 12px 12px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #D3E3FD !important;
        color: #0B57D0 !important;
    }
    .stTabs [aria-selected="true"] p {
        color: #0B57D0 !important;
    }
    
    /* 6. 指標數字 */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        color: #0B57D0 !important;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        color: #444746 !important;
    }
    
    /* 7. 表格優化 */
    [data-testid="stDataFrame"] {
        background-color: white;
        border-radius: 12px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線功能 ---
def connect_to_gsheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 找不到 Secrets 設定！")
            st.stop()
        
        key_dict = json.loads(st.secrets["gcp_service_account"], strict=False)
        creds = Credentials.from_service_account_info(key_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return sheet
    except Exception as e:
        st.error(f"連線失敗：{e}")
        st.stop()

def load_data():
    sheet = connect_to_gsheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["日期", "類型", "類別", "金額", "備註"])
    return df

def save_new_entry(date, item_type, category, amount, note):
    sheet = connect_to_gsheet()
    date_str = date.strftime("%Y-%m-%d")
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["日期", "類型", "類別", "金額", "備註"])
    sheet.append_row([date_str, item_type, category, amount, note])

def update_sheet_data(df):
    sheet = connect_to_gsheet()
    sheet.clear()
    if not df.empty:
        df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    data_to_write = [df.columns.values.tolist()] + df.values.tolist()
    sheet.update(data_to_write)

# --- 3. 介面設計 ---
st.markdown("# ☁️ 雲端記帳簿")

# Tabs 分頁
tab1, tab2, tab3 = st.tabs(["新增紀錄", "收支報表", "資料管理"])

# ==========================
# 分頁 1: 新增收支
# ==========================
with tab1:
    with st.container(border=True):
        st.markdown("### 📝 記一筆")
        
        c1, c2 = st.columns(2)
        with c1:
            date_input = st.date_input("日期")
        with c2:
            type_input = st.radio("類型", ["支出", "收入"], horizontal=True)
        
        if type_input == "支出":
            cat_options = ["飲食", "交通", "購物", "娛樂", "居家", "醫療
