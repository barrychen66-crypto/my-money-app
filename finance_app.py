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

# --- CSS 樣式注入：高對比、大字體、成熟風格 ---
st.markdown("""
    <style>
    /* 1. 整體背景：暖奶油白 (護眼、對比高) */
    .stApp {
        background-color: #FFFDF5;
    }
    
    /* 2. 標題與文字全面放大，顏色加深 */
    h1 {
        color: #2c3e50 !important;
        font-size: 3rem !important; /* 特大標題 */
        font-weight: 800 !important;
    }
    h2, h3, .stMarkdown h3 {
        color: #2c3e50 !important; 
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    p, .stMarkdown p {
        font-size: 1.2rem !important;
        color: #333333 !important;
    }
    
    /* 3. 輸入框標籤 (日期、金額那些字) */
    .stSelectbox label, .stDateInput label, .stNumberInput label, .stTextInput label, .stRadio label {
        font-size: 1.5rem !important; /* 放大標籤 */
        color: #000000 !important; /* 純黑字體，最高對比 */
        font-weight: 700 !important;
    }
    
    /* 4. 按鈕優化：酒紅色 (Burgundy) + 超大尺寸 */
    div.stButton > button {
        background-color: #800020; /* 酒紅 */
        color: white;
        border-radius: 10px;
        height: 4em; /* 按鈕變高，好按 */
        font-size: 22px !important; /* 按鈕字變大 */
        font-weight: bold;
        border: 2px solid #500015;
    }
    div.stButton > button:hover {
        background-color: #A52A2A; /* 淺一點的紅 */
        color: white;
        border-color: #800020;
    }

    /* 5. 分頁籤：加大、加深 */
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background-color: #EFEFEF;
        color: #333;
        font-size: 20px; /* 分頁字體放大 */
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #800020 !important;
        color: white !important;
    }
    
    /* 6. 指標數字放大 */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #800020 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 1.2rem !important;
        font-weight: bold;
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
        
        # 讀取 Secrets
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
tab1, tab2, tab3 = st.tabs(["大字記帳", "收支報表", "資料管理"])

# ==========================
# 分頁 1: 新增收支 (大字版)
# ==========================
with tab1:
    with st.container(border=True):
        st.markdown("### 📝 新增一筆紀錄")
        
        c1, c2 = st.columns(2)
        with c1:
            date_input = st.date_input("日期")
        with c2:
            # Radio 樣式
            type_input = st.radio("類型", ["支出", "收入"], horizontal=True)
        
        if type_input == "支出":
            cat_options = ["飲食", "交通", "購物", "娛樂", "居家", "醫療", "保險", "人情", "其他"]
        else:
            cat_options = ["薪資", "獎金", "投資", "兼職", "租金", "其他"]
            
        category_input = st.selectbox("分類", cat_options)
        
        # 預設為空，方便輸入
        amount_input = st.number_input("金額 (新台幣)", min_value=0, step=1, value=None, placeholder="點此輸入金額")
        
        note_input = st.text_input("備註 (選填)", placeholder="例如：午餐")
        
        st.write("") # 留白
        
        # 存檔按鈕
        if st.button("確認存檔", type="primary", use_container_width=True):
            if amount_input is None or amount_input == 0:
                st.warning("⚠️ 請輸入金額！")
            else:
                with st.spinner("正在上傳..."):
                    save_new_entry(date_input, type_input, category_input, amount_input, note_input)
                st.success("✅ 存檔成功！")
                st.rerun()

# 讀取資料
df = load_data()

# ==========================
# 分頁 2: 收支報表 (修復版)
# ==========================
with tab2:
    st.markdown("### 📊 財務分析")
    if df.empty:
        st.info("目前尚無資料。")
    else:
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        df["日期"] = pd.to_datetime(df["日期"])

        # --- 時間篩選器 ---
        time_period = st.selectbox("選擇統計範圍", ["本月", "近三個月", "本年度", "全部資料", "自訂範圍"])

        today = pd.Timestamp.today()
        # 預設值 (避免報錯)
        start_date = df["日期"].min()
        end_date = df["日期"].max()

        if time_period == "本月": 
            start_date = today.replace(day=1)
            end_date = today + pd.Timedelta(days=1)
        elif time_period == "近三個月": 
            start_date = today - pd.Timedelta(days=90)
            end_date =
