import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

# --- 1. 設定區 ---
# ⚠️ 請將下方網址換成您自己的 Google 試算表網址！
SHEET_URL = "https://docs.google.com/spreadsheets/d/174jupio-yaY3ckuh6ca6I3UP0DAEn7ZFwI4ilNwm0FM/edit?gid=0#gid=0"

st.set_page_config(page_title="粉紅記帳本", layout="centered", page_icon="🎀")

# --- CSS 樣式注入：粉色系 + 手機大字體優化 ---
st.markdown("""
    <style>
    /* 1. 整體背景設為淡粉色 */
    .stApp {
        background-color: #FFF0F5;
    }
    
    /* 2. 標題顏色改為深粉紅 */
    h1, h2, h3 {
        color: #C71585 !important;
        font-weight: 700 !important;
    }
    
    /* 3. 按鈕優化：變成粉紅色、變大(方便手機點擊) */
    div.stButton > button {
        background-color: #FF69B4;
        color: white;
        border-radius: 12px;
        height: 3em; 
        font-size: 20px !important;
        font-weight: bold;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #FF1493;
        color: white;
    }

    /* 4. 輸入框與文字大小加大 (手機好閱讀) */
    .stSelectbox label, .stDateInput label, .stNumberInput label, .stTextInput label {
        font-size: 1.2rem !important;
        color: #C71585 !important;
        font-weight: bold;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        min-height: 50px;
    }
    
    /* 5. 分頁籤樣式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #FFC0CB;
        border-radius: 4px 4px 0px 0px;
        color: white;
        font-size: 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF69B4 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心連線功能 (維持不變，確保穩定) ---
def connect_to_gsheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 找不到 Secrets 設定！")
            st.stop()
        
        # 讀取 Secrets (strict=False 容錯模式)
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
st.markdown("# 🎀 雲端記帳本")

# 手機版直式設計：使用 Tabs 分頁切換功能
tab1, tab2, tab3 = st.tabs(["➕ 記一筆", "📊 看報表", "📝 改紀錄"])

# ==========================
# 分頁 1: 記一筆 (直式大字體)
# ==========================
with tab1:
    with st.container(border=True):
        st.markdown("### ✨ 新增收支")
        
        # 改為直式排列，手機不用左右看
        date_input = st.date_input("📅 日期")
        
        # 使用 Radio 按鈕，手機點擊比下拉選單快
        type_input = st.radio("💰 類型", ["支出", "收入"], horizontal=True)
        
        if type_input == "支出":
            cat_options = ["😋 餐飲", "🚌 交通", "🛍️ 購物", "🎬 娛樂", "🏠 房租", "💊 醫療", "💅 美容", "🐈 寵物", "🎁 社交", "其他"]
        else:
            cat_options = ["💼 薪資", "🧧 獎金", "📈 投資", "🤝 兼職", "其他"]
            
        category_input = st.selectbox("📂 選擇類別", cat_options)
        
        # 金額輸入：預設為空 (value=None)，顯示提示文字
        amount_input = st.number_input("💲 金額 (NT$)", min_value=0, step=1, value=None, placeholder="點擊輸入金額...")
        
        note_input = st.text_input("📝 備註 (選填)", placeholder="例如：午餐、奶茶...")
        
        st.write("") # 留白
        
        if st.button("💖 確認存檔", type="primary", use_container_width=True):
            if amount_input is None or amount_input == 0:
                st.warning("⚠️ 記得輸入金額喔！")
            else:
                with st.spinner("☁️ 正在上傳雲端..."):
                    save_new_entry(date_input, type_input, category_input, amount_input, note_input)
                st.balloons() # 成功時會有氣球特效
                st.success("✅ 記帳成功！")
                st.rerun()

# 預先讀取資料
df = load_data()

# ==========================
# 分頁 2: 看報表 (粉色圖表)
# ==========================
with tab2:
    st.markdown("### 📊 收支分析")
    if df.empty:
        st.info("📭 目前還沒有資料，快去記第一筆吧！")
    else:
        # 資料處理
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        df["日期"] = pd.to_datetime(df["日期"])

        # 簡單的時間篩選
        time_period = st.selectbox("📅 統計範圍", ["本月", "近三個月", "全部"])

        today = pd.Timestamp.today()
        if time_period == "本月": 
            start_date = today.replace(day=1)
        elif time_period == "近三個月": 
            start_date = today - pd.Timedelta(days=90)
        else: 
            start_date = df["日期"].min()

        filtered_df = df[df["日期"] >= start_date]

        # 計算金額
        total_income = filtered_df[filtered_df["類型"] == "收入"]["金額"].sum()
        total_expense = filtered_df[filtered_df["類型"] == "支出"]["金額"].sum()
        net_profit = total_income - total_expense

        # 直式顯示指標 (手機比較好閱讀)
        st.container(border=True).metric("💰 總收入", f"NT$ {total_income:,.0f}")
        st.container(border=True).metric("💸 總支出", f"NT$ {total_expense:,.0f}")
        
        # 淨結餘特別標示
        with st.container(border=True):
            st.metric("猪公存了", f"NT$ {net_profit:,.0f}", delta="存下" if net_profit > 0 else "透支")

        st.divider()

        # 圓餅圖：使用粉色系配色
        st.subheader("🍰 錢錢花去哪了？")
        expense_data = filtered_df[filtered_df["類型"] == "支出"]
        
        if not expense_data.empty:
            # 定義粉色系色票
            pink_colors = ['#FF69B4', '#FFB6C1', '#FFC0CB', '#DB7093', '#C71585', '#D8BFD8', '#DDA0DD', '#EE82EE']
            
            fig = px.pie(expense_data, values='金額', names='類別', hole=0.5, 
                         color_discrete_sequence=pink_colors)
            
            # 更新圖表文字格式為 NT$
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("這段時間沒有支出紀錄喔！")

# ==========================
# 分頁 3: 改紀錄 (NT$ 顯示)
# ==========================
with tab3:
    st.markdown("### 📝 紀錄管理")
    if df.empty:
        st.write("無資料")
    else:
        st.info("💡 勾選左邊框框可刪除，點擊表格內容可修改。")
        
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
                "日期": st.column_config.DateColumn("日期", format="YYYY-MM-DD"),
                "類型": st.column_config.SelectboxColumn("類型", options=["支出", "收入"], width="small"),
                "類別": st.column_config.SelectboxColumn("類別", options=["餐飲", "交通", "購物", "娛樂", "薪資", "其他"], width="medium"),
                "金額": st.column_config.NumberColumn("金額", format="NT$%d"), # ✅ 這裡設定表格顯示 NT$
                "備註": st.column_config.TextColumn("備註"),
            }
        )

        if st.button("🔄 更新資料庫", type="primary", use_container_width=True):
            final_df = edited_df[edited_df["刪除"] == False].drop(columns=["刪除"])
            with st.spinner("同步中..."):
                update_sheet_data(final_df)
            st.success("更新完成！")
            st.rerun()
