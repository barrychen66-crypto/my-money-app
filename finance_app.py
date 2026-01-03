import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

# --- 設定區 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/174jupio-yaY3ckuh6ca6I3UP0DAEn7ZFwI4ilNwm0FM/edit?gid=0#gid=0"
st.set_page_config(page_title="雲端記帳本", layout="centered", page_icon="☁️")

# --- 連線功能 (新版) ---
def connect_to_gsheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        # 讀取 Secrets
        if "gcp_service_account" not in st.secrets:
            st.error("找不到 Secrets！請檢查 Streamlit 設定。")
            st.stop()
        
        key_dict = json.loads(st.secrets["gcp_service_account"].replace('\n', '\\n'))
        creds = Credentials.from_service_account_info(key_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_url(SHEET_URL).sheet1
    except Exception as e:
        st.error(f"連線失敗：{e}")
        st.stop()

# --- 讀取資料 ---
def load_data():
    sheet = connect_to_gsheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df if not df.empty else pd.DataFrame(columns=["日期", "類型", "類別", "金額", "備註"])

# --- 存檔功能 ---
def save_new_entry(date, item_type, category, amount, note):
    sheet = connect_to_gsheet()
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["日期", "類型", "類別", "金額", "備註"])
    sheet.append_row([date.strftime("%Y-%m-%d"), item_type, category, amount, note])

# --- 主介面 ---
st.title("☁️ 雲端記帳本")

# 輸入區
with st.expander("➕ 新增收支", expanded=True):
    c1, c2 = st.columns(2)
    dt = c1.date_input("日期")
    tp = c2.selectbox("類型", ["支出", "收入"])
    cat = st.selectbox("類別", ["餐飲", "交通", "購物", "娛樂", "居住", "薪資", "其他"])
    amt = st.number_input("金額", min_value=0, step=1)
    note = st.text_input("備註")
    
    if st.button("💾 存檔", type="primary", use_container_width=True):
        save_new_entry(dt, tp, cat, amt, note)
        st.success("存檔成功！")
        st.rerun()

# 顯示區
df = load_data()
if not df.empty:
    st.dataframe(df)

