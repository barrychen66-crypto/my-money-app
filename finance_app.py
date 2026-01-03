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
    /* 1. 整體背景 */
    .stApp { background-color: #F0F4F9; }
    
    /* 2. 標題與一般文字 */
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
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #F0F4F9; }
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
    .stTabs [aria-selected="true"] p { color: #0B57D0 !important; }
    
    /* 6. 指標數字 */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        color: #0B57D0 !important;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] { color: #444746 !important; }
    
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
        
        # 這裡就是容易出錯的地方，請確保複製完整
        if type_input == "支出":
            cat_options = ["飲食", "交通", "購物", "娛樂", "居家", "醫療", "保險", "人情", "其他"]
        else:
            cat_options = ["薪資", "獎金", "投資", "兼職", "租金", "其他"]
            
        category_input = st.selectbox("分類", cat_options)
        
        amount_input = st.number_input("金額 (NT$)", min_value=0, step=1, value=None, placeholder="點此輸入金額")
        note_input = st.text_input("備註 (選填)", placeholder="例如：午餐")
        
        st.write("") 
        
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
# 分頁 2: 收支報表 (日期只顯示 YYYY-MM-DD)
# ==========================
with tab2:
    st.markdown("### 📊 財務分析")
    if df.empty:
        st.info("目前尚無資料。")
    else:
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        df["日期"] = pd.to_datetime(df["日期"])

        time_period = st.selectbox("選擇統計範圍", ["本月", "近三個月", "本年度", "全部資料", "自訂範圍"])

        today = pd.Timestamp.today()
        start_date = df["日期"].min()
        end_date = df["日期"].max() + pd.Timedelta(days=1)

        if time_period == "本月": 
            start_date = today.replace(day=1)
            end_date = today + pd.Timedelta(days=1)
        elif time_period == "近三個月": 
            start_date = today - pd.Timedelta(days=90)
            end_date = today + pd.Timedelta(days=1)
        elif time_period == "本年度":
            start_date = today.replace(month=1, day=1)
            end_date = today + pd.Timedelta(days=1)
        elif time_period == "全部資料":
            pass 
        elif time_period == "自訂範圍":
            st.info("請在下方選擇日期")
            c1, c2 = st.columns(2)
            d1 = c1.date_input("開始", value=today - pd.Timedelta(days=7))
            d2 = c2.date_input("結束", value=today)
            start_date = pd.Timestamp(d1)
            end_date = pd.Timestamp(d2) + pd.Timedelta(days=1)

        mask = (df["日期"] >= start_date) & (df["日期"] < end_date)
        filtered_df = df[mask]

        if filtered_df.empty:
            st.warning("⚠️ 此範圍內無資料。")
        else:
            total_income = filtered_df[filtered_df["類型"] == "收入"]["金額"].sum()
            total_expense = filtered_df[filtered_df["類型"] == "支出"]["金額"].sum()
            net_profit = total_income - total_expense

            c1, c2 = st.columns(2)
            c1.metric("總收入", f"NT$ {total_income:,.0f}")
            c2.metric("總支出", f"NT$ {total_expense:,.0f}")
            st.metric("淨結餘", f"NT$ {net_profit:,.0f}", delta="存下" if net_profit > 0 else "透支")

            st.divider()

            st.markdown("### 🍰 支出分佈圖")
            expense_data = filtered_df[filtered_df["類型"] == "支出"]
            
            if not expense_data.empty:
                gemini_colors = ['#0B57D0', '#4285F4', '#7C4DFF', '#00C853', '#1976D2', '#BBDEFB']
                fig = px.pie(expense_data, values='金額', names='類別', hole=0.5, 
                             color_discrete_sequence=gemini_colors)
                fig.update_traces(textinfo='percent+label', textfont_size=18)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("無支出紀錄。")
            
            with st.expander("🔎 詳細列表"):
                st.dataframe(
                    filtered_df.sort_values("日期", ascending=False), 
                    use_container_width=True,
                    column_config={
                        "日期": st.column_config.DateColumn("日期", format="YYYY-MM-DD"),
                        "金額": st.column_config.NumberColumn("金額", format="NT$%d"),
                    }
                )

# ==========================
# 分頁 3: 資料管理 (手機版面瘦身)
# ==========================
with tab3:
    st.markdown("### 📝 修改與刪除")
    if df.empty:
        st.write("無資料。")
    else:
        st.info("勾選框框刪除，點擊內容修改。")
        
        df_to_edit = df.copy()
        df_to_edit["刪除"] = False
        cols = df_to_edit.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        df_to_edit = df_to_edit[cols]

        edited_df = st.data_editor(
            df_to_edit,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "刪除": st.column_config.CheckboxColumn("刪除", width="small"),
                "日期": st.column_config.DateColumn("日期", format="YYYY-MM-DD", width="small"),
                "類型": st.column_config.SelectboxColumn("類型", options=["支出", "收入"], width="small"),
                "類別": st.column_config.SelectboxColumn("類別", options=["飲食", "交通", "購物", "娛樂", "薪資", "其他"], width="small"),
                "金額": st.column_config.NumberColumn("金額", format="NT$%d", width="small"),
                "備註": st.column_config.TextColumn("備註", width="medium"),
            }
        )

        st.write("")
        if st.button("🔄 更新資料庫", type="primary", use_container_width=True):
            final_df = edited_df[edited_df["刪除"] == False].drop(columns=["刪除"])
            with st.spinner("更新中..."):
                update_sheet_data(final_df)
            st.success("完成！")
            st.rerun()
