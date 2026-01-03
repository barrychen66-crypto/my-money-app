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

st.set_page_config(page_title="雅緻記帳本", layout="centered", page_icon="🌹")

# --- CSS 樣式注入：莫蘭迪乾燥玫瑰色系 (成熟穩重風格) ---
st.markdown("""
    <style>
    /* 1. 背景：溫暖的米白色 (護眼、舒適) */
    .stApp {
        background-color: #FDFCF8;
    }
    
    /* 2. 標題：深褐灰色 (沈穩) */
    h1, h2, h3, .stMarkdown h3 {
        color: #5D4037 !important; 
        font-family: "Microsoft JhengHei", sans-serif;
        font-weight: 600 !important;
    }
    
    /* 3. 按鈕：乾燥玫瑰色 (典雅不刺眼) */
    div.stButton > button {
        background-color: #BC8F8F; /* RosyBrown */
        color: white;
        border-radius: 8px;
        height: 3.2em; 
        font-size: 18px !important;
        font-weight: 500;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    div.stButton > button:hover {
        background-color: #A07070; /* Darker RosyBrown */
        color: white;
    }

    /* 4. 輸入框優化：暖灰色文字 */
    .stSelectbox label, .stDateInput label, .stNumberInput label, .stTextInput label, .stRadio label {
        font-size: 1.1rem !important;
        color: #6D4C41 !important;
        font-weight: 500;
    }
    
    /* 5. 分頁籤樣式：香檳金配色 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #F5E6E0; /* 淺粉膚色 */
        border-radius: 4px 4px 0px 0px;
        color: #6D4C41;
        font-size: 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #BC8F8F !important; /* 乾燥玫瑰 */
        color: white !important;
    }
    
    /* 6. 指標卡片：優雅邊框 */
    div[data-testid="stMetric"] {
        background-color: #FFFBF0;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #E6D5D0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* 7. 表格優化 (確保資料管理顯示正常) */
    [data-testid="stDataFrame"] {
        background-color: white;
        border-radius: 8px;
        padding: 5px;
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
        
        # 讀取 Secrets (strict=False)
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
st.markdown("# 🌹 雅緻記帳本")

# Tabs 分頁
tab1, tab2, tab3 = st.tabs(["記一筆", "收支報表", "帳務管理"])

# ==========================
# 分頁 1: 新增收支
# ==========================
with tab1:
    with st.container(border=True):
        st.markdown("### 📝 新增紀錄")
        
        date_input = st.date_input("日期")
        
        # Radio 樣式
        type_input = st.radio("類型", ["支出", "收入"], horizontal=True)
        
        if type_input == "支出":
            cat_options = ["飲食", "交通", "購物", "娛樂", "居家", "醫療", "保險", "人情", "其他"]
        else:
            cat_options = ["薪資", "獎金", "投資", "兼職", "租金", "其他"]
            
        category_input = st.selectbox("分類", cat_options)
        
        # 預設為空，方便輸入 (修復了這裡的語法錯誤)
        amount_input = st.number_input("金額 (NT$)", min_value=0, step=1, value=None, placeholder="請輸入金額")
        
        note_input = st.text_input("備註", placeholder="選填")
        
        st.write("")
        
        if st.button("確認存檔", type="primary", use_container_width=True):
            if amount_input is None or amount_input == 0:
                st.warning("請輸入有效的金額。")
            else:
                with st.spinner("資料同步中..."):
                    save_new_entry(date_input, type_input, category_input, amount_input, note_input)
                st.success("✅ 已成功記錄！")
                st.rerun()

# 讀取資料
df = load_data()

# ==========================
# 分頁 2: 收支報表 (含自訂範圍)
# ==========================
with tab2:
    st.markdown("### 📊 財務分析")
    if df.empty:
        st.info("目前尚無資料。")
    else:
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        df["日期"] = pd.to_datetime(df["日期"])

        # --- 時間篩選器 (新增自訂範圍) ---
        col_select, _ = st.columns([2,1])
        with col_select:
            time_period = st.selectbox("統計期間", ["本月", "近三個月", "本年度", "全部", "自訂範圍"])

        today = pd.Timestamp.today()
        start_date
