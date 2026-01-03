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

st.set_page_config(page_title="理財記帳本", layout="centered", page_icon="💎")

# --- CSS 樣式注入：Tiffany 藍成熟風格 + 手機優化 ---
st.markdown("""
    <style>
    /* 1. 整體背景設為極淡的薄荷白，護眼且清爽 */
    .stApp {
        background-color: #F5FFFA;
    }
    
    /* 2. 標題顏色改為沈穩的深湖水綠 */
    h1, h2, h3, .stMarkdown h3 {
        color: #008B8B !important; 
        font-family: "Microsoft JhengHei", sans-serif;
        font-weight: 600 !important;
    }
    
    /* 3. 按鈕優化：Tiffany 藍，圓角修飾，成熟大方 */
    div.stButton > button {
        background-color: #0ABAB5; /* Tiffany Blue */
        color: white;
        border-radius: 8px;
        height: 3.2em; 
        font-size: 18px !important;
        font-weight: 500;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    div.stButton > button:hover {
        background-color: #20B2AA; /* Light Sea Green */
        color: white;
    }

    /* 4. 輸入框優化 */
    .stSelectbox label, .stDateInput label, .stNumberInput label, .stTextInput label, .stRadio label {
        font-size: 1.1rem !important;
        color: #2F4F4F !important; /* Dark Slate Gray */
        font-weight: 500;
    }
    
    /* 5. 分頁籤樣式：簡約風格 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #E0FFFF;
        border-radius: 4px 4px 0px 0px;
        color: #555;
        font-size: 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0ABAB5 !important;
        color: white !important;
    }
    
    /* 6. 指標卡片邊框 */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #E0FFFF;
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
st.markdown("# 💎 理財記帳本")

# Tabs 分頁
tab1, tab2, tab3 = st.tabs(["新增收支", "收支報表", "帳務管理"])

# ==========================
# 分頁 1: 新增收支
# ==========================
with tab1:
    with st.container(border=True):
        st.markdown("### 📝 記一筆")
        
        date_input = st.date_input("日期")
        
        # Radio 樣式
        type_input = st.radio("類型", ["支出", "收入"], horizontal=True)
        
        if type_input == "支出":
            cat_options = ["飲食", "交通", "購物", "娛樂", "居家", "醫療", "保險", "人情", "其他"]
        else:
            cat_options = ["薪資", "獎金", "投資", "兼職", "租金", "其他"]
            
        category_input = st.selectbox("分類", cat_options)
        
        # 預設為空，方便輸入
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
        start_date = df["日期"].min()
        end_date = df["日期"].max() # 預設結束時間

        if time_period == "本月": 
            start_date = today.replace(day=1)
            end_date = today
        elif time_period == "近三個月": 
            start_date = today - pd.Timedelta(days=90)
            end_date = today
        elif time_period == "本年度":
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif time_period == "全部":
            pass # 維持預設的 min 和 max
        elif time_period == "自訂範圍":
            st.info("請選擇開始與結束日期")
            c1, c2 = st.columns(2)
            d1 = c1.date_input("開始日期", value=today - pd.Timedelta(days=7))
            d2 = c2.date_input("結束日期", value=today)
            start_date = pd.Timestamp(d1)
            end_date = pd.Timestamp(d2) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) # 包含當天結束

        # 進行篩選
        filtered_df = df[(df["日期"] >= start_date) & (df["日期"] <= end_date)]

        if filtered_df.empty:
            st.warning("⚠️ 選擇的日期範圍內沒有資料。")
        else:
            # 計算金額
            total_income = filtered_df[filtered_df["類型"] == "收入"]["金額"].sum()
            total_expense = filtered_df[filtered_df["類型"] == "支出"]["金額"].sum()
            net_profit = total_income - total_expense

            # 顯示指標 (Metric)
            c1, c2 = st.columns(2)
            c1.metric("總收入", f"NT$ {total_income:,.0f}")
            c2.metric("總支出", f"NT$ {total_expense:,.0f}")
            st.metric("淨結餘", f"NT$ {net_profit:,.0f}", delta="結餘" if net_profit > 0 else "透支")

            st.divider()

            # 圓餅圖：Tiffany 藍色系
            st.subheader("支出類別佔比")
            expense_data = filtered_df[filtered_df["類型"] == "支出"]
            
            if not expense_data.empty:
                # 定義 Tiffany/Teal 色系
                teal_colors = ['#0ABAB5', '#40E0D0', '#20B2AA', '#00CED1', '#5F9EA0', '#4682B4', '#B0E0E6']
                
                fig = px.pie(expense_data, values='金額', names='類別', hole=0.5, 
                             color_discrete_sequence=teal_colors)
                fig.update_traces(textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("此區間無支出紀錄。")
            
            # 顯示明細表格
            with st.expander("查看詳細列表"):
                st.dataframe(filtered_df.sort_values("日期", ascending=False), use_container_width=True)

# ==========================
# 分頁 3: 帳務管理
# ==========================
with tab3:
    st.markdown("### 📝 資料維護")
    if df.empty:
        st.write("目前無資料")
    else:
        st.caption("勾選「刪除」後按更新，或直接修改內容。")
        
        df_to_edit = df.copy()
        df_to_edit["刪除"] = False
        cols = df_to_edit.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        df_to_edit = df_to_edit
