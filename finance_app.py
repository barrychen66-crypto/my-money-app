import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px

# --- 1. 設定區 ---
# ⚠️ 請將下方網址換成您自己的 Google 試算表網址！
SHEET_URL = "https://docs.google.com/spreadsheets/d/174jupio-yaY3ckuh6ca6I3UP0DAEn7ZFwI4ilNwm0FM/edit?gid=0#gid=0"

st.set_page_config(page_title="雲端記帳本 Pro", layout="centered", page_icon="💰")

# --- 2. 核心功能：連線 Google Sheets ---
def connect_to_gsheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("❌ 找不到 Secrets 設定！")
            st.stop()
            
        # ✅ 使用 strict=False 確保能讀取有換行的 Secrets
        key_dict = json.loads(st.secrets["gcp_service_account"], strict=False)
        creds = Credentials.from_service_account_info(key_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return sheet
    except Exception as e:
        st.error(f"連線失敗：{e}")
        st.stop()

# 讀取資料
def load_data():
    sheet = connect_to_gsheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # 如果是空的，回傳一個有欄位的空表
    if df.empty:
        return pd.DataFrame(columns=["日期", "類型", "類別", "金額", "備註"])
    return df

# 新增資料
def save_new_entry(date, item_type, category, amount, note):
    sheet = connect_to_gsheet()
    date_str = date.strftime("%Y-%m-%d")
    # 如果試算表完全沒標題，先補上標題
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["日期", "類型", "類別", "金額", "備註"])
    sheet.append_row([date_str, item_type, category, amount, note])

# 刪除或更新資料 (透過重寫整個工作表)
def update_sheet_data(df):
    sheet = connect_to_gsheet()
    sheet.clear() # 清空舊資料
    # 準備要寫入的資料 (包含標題)
    # 處理日期格式，確保寫入字串
    if not df.empty:
        df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
    data_to_write = [df.columns.values.tolist()] + df.values.tolist()
    sheet.update(data_to_write)

# --- 3. 介面設計 ---
st.title("💰 我的雲端記帳本")

# 建立三個分頁：記帳、報表、管理
tab1, tab2, tab3 = st.tabs(["➕ 新增收支", "📊 分析報表", "📝 紀錄管理"])

# ==========================
# 分頁 1: 新增收支
# ==========================
with tab1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        date_input = c1.date_input("日期")
        type_input = c2.selectbox("類型", ["支出", "收入"])
        
        # 根據類型切換類別選項
        if type_input == "支出":
            cat_options = ["餐飲", "交通", "購物", "娛樂", "房租", "保險", "醫療", "其他", "居家", "孝親"]
        else:
            cat_options = ["薪資", "獎金", "股息", "兼職", "投資", "其他"]
        category_input = st.selectbox("類別", cat_options)
        
        # ✅ 改良：使用 value=None 讓預設為空，並加上 placeholder
        amount_input = st.number_input("金額 (NT$)", min_value=0, step=1, value=None, placeholder="請輸入數字...")
        note_input = st.text_input("備註 (選填)")
        
        if st.button("💾 確認存檔", type="primary", use_container_width=True):
            if amount_input is None or amount_input == 0:
                st.warning("⚠️ 請輸入有效的金額！")
            else:
                with st.spinner("正在上傳雲端..."):
                    save_new_entry(date_input, type_input, category_input, amount_input, note_input)
                st.success("✅ 存檔成功！")
                st.rerun()

# 先讀取資料供後面使用
df = load_data()

# ==========================
# 分頁 2: 分析報表
# ==========================
with tab2:
    if df.empty:
        st.info("目前還沒有資料，趕快去記一筆吧！")
    else:
        # 資料轉換
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        df["日期"] = pd.to_datetime(df["日期"])

        # 篩選器
        col_filter, _ = st.columns([2,1])
        with col_filter:
            time_period = st.selectbox("📅 選擇時間範圍", ["本月", "近三個月", "本年度", "全部資料"])

        today = pd.Timestamp.today()
        if time_period == "本月": 
            start_date = today.replace(day=1)
        elif time_period == "近三個月": 
            start_date = today - pd.Timedelta(days=90)
        elif time_period == "本年度": 
            start_date = today.replace(month=1, day=1)
        else: 
            start_date = df["日期"].min()

        filtered_df = df[df["日期"] >= start_date]

        # 顯示三大指標
        total_income = filtered_df[filtered_df["類型"] == "收入"]["金額"].sum()
        total_expense = filtered_df[filtered_df["類型"] == "支出"]["金額"].sum()
        net_profit = total_income - total_expense

        m1, m2, m3 = st.columns(3)
        m1.metric("總收入", f"${total_income:,.0f}", delta_color="normal")
        m2.metric("總支出", f"${total_expense:,.0f}", delta_color="inverse")
        m3.metric("淨結餘", f"${net_profit:,.0f}", delta="存下" if net_profit > 0 else "透支")

        st.divider()

        # 圓餅圖
        st.subheader("🍰 支出類別分析")
        expense_data = filtered_df[filtered_df["類型"] == "支出"]
        if not expense_data.empty:
            fig = px.pie(expense_data, values='金額', names='類別', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("這段時間沒有支出紀錄。")

# ==========================
# 分頁 3: 紀錄管理 (修改/刪除)
# ==========================
with tab3:
    st.subheader("📝 管理所有紀錄")
    if df.empty:
        st.write("目前無資料。")
    else:
        # 使用 Streamlit 的 Data Editor 讓您可以直接在網頁上修改
        st.info("💡 提示：您可以直接在表格中修改內容，或是勾選左側框框來刪除資料。修改後請務必點擊下方的「更新雲端」按鈕。")
        
        # 為了方便刪除，我們加一個「刪除」勾選欄位
        df_to_edit = df.copy()
        df_to_edit["刪除"] = False # 預設不刪除
        
        # 把「刪除」欄位放到最前面
        cols = df_to_edit.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        df_to_edit = df_to_edit[cols]

        edited_df = st.data_editor(
            df_to_edit,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "刪除": st.column_config.CheckboxColumn(
                    "刪除?",
                    help="勾選後按下方按鈕即可刪除此行",
                    default=False,
                ),
                "日期": st.column_config.DateColumn("日期", format="YYYY-MM-DD"),
                "金額": st.column_config.NumberColumn("金額", format="$%d"),
            }
        )

        # 更新按鈕
        if st.button("🔄 確認修改並更新雲端", type="primary"):
            # 1. 篩選掉被勾選「刪除」的資料
            final_df = edited_df[edited_df["刪除"] == False].drop(columns=["刪除"])
            
            # 2. 寫回 Google Sheets
            with st.spinner("正在同步資料到 Google Sheets..."):
                update_sheet_data(final_df)
            
            st.success("✅ 更新完成！")
            st.rerun()
