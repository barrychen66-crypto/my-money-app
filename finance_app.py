import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

# --- 1. 設定區 ---
# ⚠️ 請將下方網址換成您自己的 Google 試算表網址！
SHEET_URL = "https://docs.google.com/spreadsheets/d/174jupio-yaY3ckuh6ca6I3UP0DAEn7ZFwI4ilNwm0FM/edit?gid=0#gid=0"

st.set_page_config(page_title="雲端記帳本", layout="centered", page_icon="☁️")

# --- 2. 連線 Google Sheets 的核心功能 ---
def connect_to_gsheet():
    # --- 設定權限範圍 ---
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

    # --- 關鍵修改：從 Secrets 讀取憑證 ---
    try:
        # 1. 讀取 Secrets 裡的字串並轉為字典
        # 這裡會抓取您在 Streamlit 網頁上設定的 secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 找不到 Secrets 設定！請檢查 Streamlit 的 Secrets 頁面。")
            st.stop()
            
        key_dict = json.loads(st.secrets["gcp_service_account"])
        
        # 2. 使用字典建立憑證
        creds = Credentials.from_service_account_info(key_dict, scopes=scope)
        
        # 3. 連線 Google Sheets
        client = gspread.authorize(creds)
        
        # 4. 開啟試算表
        sheet = client.open_by_url(SHEET_URL).sheet1
        return sheet
        
    except Exception as e:
        st.error(f"❌ 連線失敗！原因：{e}")
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
    # 如果是全空的表，先寫入標題
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["日期", "類型", "類別", "金額", "備註"])
    sheet.append_row([date_str, item_type, category, amount, note])

# --- 3. 介面設計 ---
st.markdown("### ☁️ 我的雲端記帳本 (網址連線版)")

# --- 輸入區 ---
with st.container(border=True):
    with st.expander("➕ 點擊新增一筆收支", expanded=False):
        c1, c2 = st.columns(2)
        date_input = c1.date_input("日期")
        type_input = c2.selectbox("類型", ["支出", "收入"])
        
        if type_input == "支出":
            cat_options = ["餐飲", "交通", "購物", "娛樂", "房租", "保險", "醫療", "其他", "居家", "孝親"]
        else:
            cat_options = ["薪資", "獎金", "股息", "兼職", "投資", "其他"]
        category_input = st.selectbox("類別", cat_options)
        
        amount_input = st.number_input("金額 (NT$)", min_value=0, step=1)
        note_input = st.text_input("備註 (選填)")
        
        if st.button("💾 上傳雲端", type="primary", use_container_width=True):
            with st.spinner("正在連線 Google..."):
                save_new_entry(date_input, type_input, category_input, amount_input, note_input)
            st.success("✅ 已儲存！請去試算表看看有沒有出現？")
            st.rerun()

st.write("") 

# --- 數據展示區 ---
with st.spinner("正在讀取雲端資料..."):
    df = load_data()

if df.empty:
    st.info("👆 目前雲端是空的，快記下第一筆帳吧！")
else:
    # 簡單的數據處理
    df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
    df["日期"] = pd.to_datetime(df["日期"])

    col_filter, _ = st.columns([2,1])
    with col_filter:
        time_period = st.selectbox("查看範圍", ["近一週", "近一個月", "近三個月", "本年度", "全部"])

    today = pd.Timestamp.today()
    if time_period == "近一週": start_date = today - pd.Timedelta(days=7)
    elif time_period == "近一個月": start_date = today - pd.Timedelta(days=30)
    elif time_period == "近三個月": start_date = today - pd.Timedelta(days=90)
    elif time_period == "本年度": start_date = today.replace(month=1, day=1)
    else: start_date = df["日期"].min()

    filtered_df = df[df["日期"] >= start_date]

    if not filtered_df.empty:
        total_income = filtered_df[filtered_df["類型"] == "收入"]["金額"].sum()
        total_expense = filtered_df[filtered_df["類型"] == "支出"]["金額"].sum()
        net_profit = total_income - total_expense

        c1, c2, c3 = st.columns(3)
        c1.metric("總收入", f"${total_income:,.0f}")
        c2.metric("總支出", f"${total_expense:,.0f}")
        c3.metric("淨損益", f"${net_profit:,.0f}", delta="獲利" if net_profit > 0 else "虧損")
        
        st.write("")
        tab1, tab2 = st.tabs(["📊 圖表", "📝 明細"])
        
        with tab1:
            expense_data = filtered_df[filtered_df["類型"] == "支出"]
            if not expense_data.empty:
                fig = px.pie(expense_data, values='金額', names='類別', hole=0.6)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("無支出")

        with tab2:
            st.dataframe(filtered_df.sort_values("日期", ascending=False), use_container_width=True)
