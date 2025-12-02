# Phone_Shop_SQLite_System.py
import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, date, timedelta

# --------------------------
# DB setup
# --------------------------
DB_FILE = "phone_shop.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
# keep a mapping of table -> expected columns (to preserve original logic)
TABLE_SCHEMAS = {}

def register_table(name, columns):
    TABLE_SCHEMAS[name] = columns

def init_table(table, columns):
    """Create table if not exists. If exists, add missing columns. Do not remove existing columns.
       Columns are created as TEXT; numeric handling is done with pandas later."""
    register_table(table, columns)
    cur = conn.cursor()
    # create table if not exists with given columns
    # Build CREATE TABLE ... (col1 TEXT, col2 TEXT, ...)
    if not table_exists(table):
        cols_def = ", ".join([f"'{c}' TEXT" for c in columns])
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{table}' ({cols_def})")
        conn.commit()
    else:
        # check columns and add missing with ALTER TABLE ADD COLUMN
        existing = get_table_columns(table)
        for c in columns:
            if c not in existing:
                cur.execute(f"ALTER TABLE '{table}' ADD COLUMN '{c}' TEXT")
        conn.commit()

def table_exists(table):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cur.fetchone() is not None

def get_table_columns(table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table}')")
    rows = cur.fetchall()
    return [r[1] for r in rows]

# --------------------------
# DB read/write helpers (keeps same semantics as Excel version)
# --------------------------
def load_data(table):
    """Returns a pandas.DataFrame for the given table.
       Ensures the DataFrame has at least the expected columns in TABLE_SCHEMAS[table] order."""
    if not table_exists(table):
        # return empty df with expected columns if known
        cols = TABLE_SCHEMAS.get(table, [])
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_sql_query(f"SELECT * FROM '{table}'", conn)
    except Exception:
        # on error return empty with expected cols
        cols = TABLE_SCHEMAS.get(table, [])
        return pd.DataFrame(columns=cols)
    # ensure expected columns exist and are ordered
    expected = TABLE_SCHEMAS.get(table)
    if expected:
        for c in expected:
            if c not in df.columns:
                df[c] = pd.NA
        # reorder to expected (also keep extra columns at end)
        ordered = [c for c in expected if c in df.columns]
        extra = [c for c in df.columns if c not in ordered]
        df = df[ordered + extra]
    return df

def overwrite_data(table, df):
    """Replace the table contents with the DataFrame (atomic via SQL replace)."""
    # pandas to_sql with if_exists='replace'
    df.to_sql(table, conn, if_exists='replace', index=False)

def save_row(table, new_row):
    """Append a row safely: load, append, write back. Raises ValueError if column count mismatch."""
    df = load_data(table)
    # if df has no columns but we have expected schema, create DataFrame with expected columns
    if df is None or (df.empty and (not df.columns.any()) and table in TABLE_SCHEMAS):
        df = pd.DataFrame(columns=TABLE_SCHEMAS[table])
    if len(new_row) != len(df.columns):
        raise ValueError(f"عدد الأعمدة لا يطابق ({len(new_row)} != {len(df.columns)})")
    df.loc[len(df)] = new_row
    overwrite_data(table, df)

def add_log(action):
    try:
        save_row(LOG_FILE, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action])
    except Exception:
        # if logging fails silently ignore (don't break UI)
        pass

def next_id(table, col="المعرف"):
    df = load_data(table)
    if df.empty or col not in df.columns:
        return 1
    try:
        vals = pd.to_numeric(df[col], errors='coerce')
        if vals.isnull().all():
            return 1
        return int(vals.max()) + 1
    except Exception:
        return 1

# --------------------------
# Table (previously file) names -- keep same variable names to minimize changes
# --------------------------
CASH_FILE = "cash"
PRODUCTS_FILE = "products"
MACHINE_FILE = "machines"
MACHINE_DAILY_FILE = "machines_daily"
MACHINE_DAY_META_FILE = "machines_day_meta"
DEBTS_FILE = "debts"
LOG_FILE = "logs"
PROFIT_FILE = "profits"

SALES_FILE = "sales"
SALES_SUMMARY_FILE = "sales_summary"
MACHINE_COLLECTION_FILE = "machine_collection"

DEBTS_DAILY_FILE = "debts_daily"
DEBTS_ARCHIVE_FILE = "debts_archive"
DEBTS_DAILY_SUMMARY_FILE = "debts_daily_summary"
OUTSTANDING_FILE = "debts_outstanding"

PAYMENTS_DAILY_FILE = "payments_daily"
PAYMENTS_ARCHIVE_FILE = "payments_archive"
PAYMENTS_DAILY_SUMMARY_FILE = "payments_daily_summary"

DAMAGED_FILE = "damaged"

# --------------------------
# Initialize tables with your columns
# --------------------------
init_table(CASH_FILE, ["المصدر", "الرصيد"])
init_table(PRODUCTS_FILE, ["التاريخ", "الفئة", "النوع", "السعر", "الكمية"])
init_table(MACHINE_FILE, ["التاريخ", "المكنة", "رصيد الفتح", "رصيد مضاف", "رصيد نهاية", "المباع (للدُرج)"])
init_table(MACHINE_DAILY_FILE, ["المكنة", "رصيد الفتح", "رصيد مضاف", "رصيد نهاية"])
init_table(MACHINE_DAY_META_FILE, ["التاريخ", "تحصيل الشركة (إجمالي)", "فلوس الدُرج قبل التحصيل", "فلوس معايا بعد التحصيل", "فلوس معايا تراكمي"])
init_table(MACHINE_COLLECTION_FILE, ["التاريخ", "المكنة", "تحصيل يومي"])
init_table(DEBTS_FILE, ["الاسم", "الحالة", "المبلغ"])
init_table(LOG_FILE, ["التاريخ والوقت", "العملية"])
init_table(PROFIT_FILE, ["التاريخ", "المكسب"])
init_table(SALES_FILE, ["المعرف", "التاريخ", "الفئة", "النوع", "السعر", "الكمية", "الإجمالي"])
init_table(SALES_SUMMARY_FILE, ["التاريخ", "إجمالي المبيعات", "عدد العمليات"])

init_table(DEBTS_DAILY_FILE, ["المعرف", "التاريخ", "الاسم", "المبلغ"])
init_table(DEBTS_ARCHIVE_FILE, ["المعرف", "التاريخ", "الاسم", "المبلغ"])
init_table(DEBTS_DAILY_SUMMARY_FILE, ["التاريخ", "إجمالي الديون", "عدد الأشخاص"])
init_table(OUTSTANDING_FILE, ["الاسم", "الرصيد"])

init_table(PAYMENTS_DAILY_FILE, ["المعرف", "التاريخ", "الاسم", "المبلغ"])
init_table(PAYMENTS_ARCHIVE_FILE, ["المعرف", "التاريخ", "الاسم", "المبلغ"])
init_table(PAYMENTS_DAILY_SUMMARY_FILE, ["التاريخ", "إجمالي المدفوع", "عدد الأشخاص"])
init_table(DAMAGED_FILE, ["التاريخ", "الفئة", "النوع", "السعر", "الكمية", "سبب التالف"])
init_table("free_number", ["القيمة"])
# --------------------------
# Utility safe conversion used everywhere
# --------------------------
def safe_int(x):
    try:
        if x is None:
            return 0
        if pd.isna(x):
            return 0
        return int(float(x))
    except Exception:
        try:
            return int(x)
        except Exception:
            return 0

# --------------------------
# Inventory helpers (unchanged logic, only load/save use DB)
# --------------------------
def available_qty(category, type_, price):
    products = load_data(PRODUCTS_FILE)
    if products.empty:
        return 0
    mask = (products['الفئة'] == category) & (products['النوع'] == type_) & (products['السعر'] == price)
    return int(pd.to_numeric(products.loc[mask, 'الكمية'], errors='coerce').fillna(0).sum())

def deduct_from_inventory(category, type_, price, qty):
    products = load_data(PRODUCTS_FILE)
    if products.empty:
        return False
    # FIX: use 'السعر' instead of 'سعر'
    mask = (products['الفئة'] == category) & (products['النوع'] == type_) & (products['السعر'] == price)
    if products.loc[mask].empty:
        return False
    products.loc[mask, 'الكمية'] = pd.to_numeric(products.loc[mask, 'الكمية'], errors='coerce').fillna(0) - qty
    products = products[~((pd.to_numeric(products['الكمية'], errors='coerce').fillna(0) <= 0) & mask)]
    overwrite_data(PRODUCTS_FILE, products)
    return True

def add_back_to_inventory(category, type_, price, qty):
    save_row(PRODUCTS_FILE, [datetime.now().date(), category, type_, price, qty])

# --------------------------
# Debts/Payments helpers (Sales page)
# --------------------------
def _get_outstanding_df():
    df = load_data(OUTSTANDING_FILE)
    if not df.empty:
        df['الرصيد'] = pd.to_numeric(df['الرصيد'], errors='coerce').fillna(0.0)
    else:
        df = pd.DataFrame(columns=["الاسم", "الرصيد"])
    return df

def adjust_outstanding(name: str, delta: float):
    name = str(name).strip()
    if not name:
        return
    out_df = _get_outstanding_df()
    if out_df.empty or name not in list(out_df['الاسم']):
        if delta > 0:
            save_row(OUTSTANDING_FILE, [name, float(delta)])
        return
    idx = out_df[out_df['الاسم'] == name].index[0]
    new_bal = float(out_df.at[idx, 'الرصيد']) + float(delta)
    if new_bal <= 0:
        out_df = out_df.drop(idx)
    else:
        out_df.at[idx, 'الرصيد'] = new_bal
    overwrite_data(OUTSTANDING_FILE, out_df)

def record_daily_debt(name: str, amount: float, day_str: str):
    debt_id = next_id(DEBTS_DAILY_FILE)
    save_row(DEBTS_DAILY_FILE, [debt_id, day_str, name, float(amount)])
    adjust_outstanding(name, +float(amount))
    add_log(f"تسجيل دين يومي: {name} - {amount}")

def record_daily_payment(name: str, amount: float, day_str: str):
    pay_id = next_id(PAYMENTS_DAILY_FILE)
    save_row(PAYMENTS_DAILY_FILE, [pay_id, day_str, name, float(amount)])
    adjust_outstanding(name, -float(amount))
    add_log(f"تسجيل دفع يومي: {name} - {amount}")

# --------------------------
# UI Setup (unchanged)
# --------------------------
st.set_page_config(page_title="📱 نظام محل الموبايلات", layout="wide")
st.title("📱 نظام إدارة محل موبايلات")


menu = st.sidebar.radio(
    "القائمة",
    ["الكاش", "البضاعة", "المكن", "البيع", "البيع التالف/المرتجع", "مراجعة المبيعات والمخزون", "التقارير", "السجل", "الأرباح"],
)

# ==========================
# الكاش
# ==========================
if menu == "الكاش":
    st.header("📊 الكاش")

    st.subheader("🧾 المحافظ والدرج (دائمة)")
    cash_data = load_data(CASH_FILE)

    if not cash_data.empty and "المصدر" in cash_data.columns:
        for i, row in cash_data.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(row.get('المصدر', 'غير محدد'))
            with col2:
                balance = st.number_input(
                    "✏️ تعديل",
                    min_value=0,
                    value=int(row.get('الرصيد', 0) if pd.notna(row.get('الرصيد')) else 0),
                    key=f"edit_cash_{i}",
                    step=1
                )
            with col3:
                if st.button("💾 حفظ", key=f"save_cash_{i}"):
                    cash_data.at[i, 'الرصيد'] = balance
                    overwrite_data(CASH_FILE, cash_data)
                    add_log(f"تعديل رصيد {row.get('المصدر', 'غير محدد')} إلى {balance}")
                    st.rerun()
            with col4:
                if st.button("🗑️", key=f"delete_cash_{i}"):
                    cash_data = cash_data.drop(i)
                    overwrite_data(CASH_FILE, cash_data)
                    add_log(f"حذف مصدر: {row.get('المصدر', 'غير محدد')}")
                    st.rerun()

    source = st.text_input("اسم المصدر (مثال: فودافون صغير / فودافون كبير / انستا باي / درج)")
    balance = st.number_input("الرصيد", min_value=0, value=0, step=1)
    if st.button("➕ إضافة مصدر"):
        try:
            save_row(CASH_FILE, [source, balance])
            add_log(f"إضافة مصدر: {source} برصيد {balance}")
            st.success("تمت إضافة المصدر ✅")
            st.rerun()
        except ValueError as e:
            st.error(f"خطأ في الحفظ: {e}")

    total_cash = cash_data['الرصيد'].sum() if not cash_data.empty else 0
    st.metric("💵 إجمالي الكاش", total_cash)

    st.subheader("👥 الأشخاص (ليهم / عليهم)")
    debts = load_data(DEBTS_FILE)

    if not debts.empty:
        for i, row in debts.iterrows():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
            with col1:
                st.write(row.get('الاسم', 'غير محدد'))
            with col2:
                st.write(row.get('الحالة', 'غير محدد'))
            with col3:
                amount = row['المبلغ'] if row['الحالة'] == 'ليه' else -row['المبلغ']
                st.write(amount)
            with col4:
                if st.button("🗑️", key=f"delete_debt_{i}"):
                    debts = debts.drop(i)
                    overwrite_data(DEBTS_FILE, debts)
                    add_log(f"حذف شخص: {row.get('الاسم', 'غير محدد')}")
                    st.rerun()
            with col5:
                new_amount = st.number_input(
                    "✏️ تعديل",
                    min_value=0,
                    value=int(row.get('المبلغ', 0) if pd.notna(row.get('المبلغ')) else 0),
                    key=f"edit_debt_{i}",
                    step=1
                )
                if st.button("💾 حفظ", key=f"save_debt_{i}"):
                    debts.at[i, 'المبلغ'] = new_amount
                    overwrite_data(DEBTS_FILE, debts)
                    add_log(f"تعديل شخص: {row.get('الاسم', 'غير محدد')} - {row.get('الحالة', '')} - {new_amount}")
                    st.rerun()

    # ======= التجميعات والملخصات =======
    if 'الحالة' in debts.columns if not debts.empty else False:
        debts['القيمة'] = debts.apply(lambda x: x['المبلغ'] if x['الحالة'] == 'ليه' else -x['المبلغ'], axis=1)
        total_sum = debts['القيمة'].sum()
        total_owed = debts[debts['الحالة'] == 'ليه']['المبلغ'].sum()
        total_due = debts[debts['الحالة'] == 'عليه']['المبلغ'].sum()
        c1,c2,c3 = st.columns(3)
        c1.metric("📌 مجموع ليهم (موجب)", int(total_owed))
        c2.metric("📌 مجموع عليهم (سالب)", int(-total_due))
        c3.metric("⚖️ الصافي", int(total_sum))

        st.subheader("📊 الملخص النهائي")
        profit = total_cash - total_sum
        st.metric("💰 المكسب", int(profit))

        if st.button("📅 حفظ المكسب اليومي"):
            today = datetime.now().strftime("%Y-%m-%d")
            save_row(PROFIT_FILE, [today, profit])
            add_log(f"حفظ مكسب يوم {today}: {profit}")
            st.success("تم حفظ المكسب اليومي ✅")

    name = st.text_input("اسم الشخص الجديد")
    status = st.selectbox("الحالة", ["ليه", "عليه"])
    amount = st.number_input("المبلغ", min_value=0, value=0, step=1)

    if st.button("➕ إضافة شخص"):
        try:
            save_row(DEBTS_FILE, [name, status, amount])
            add_log(f"إضافة شخص: {name} - {status} {amount}")
            st.success("تمت إضافة الشخص ✅")
            st.rerun()
        except ValueError as e:
            st.error(f"خطأ في الحفظ: {e}")


# ==========================
# البضاعة (المخزون)
# ==========================
elif menu == "البضاعة":
    st.header("📦 إدارة البضاعة")
    # واجهة رفع ملف إكسل
    st.subheader("⬆️ استيراد البضاعة من ملف Excel")
    excel_file = st.file_uploader("اختر ملف Excel", type=["xlsx", "xls", "csv"])
    if excel_file is not None:
        try:
            if excel_file.name.endswith(".csv"):
                df_excel = pd.read_csv(excel_file)
            else:
                df_excel = pd.read_excel(excel_file)
            st.dataframe(df_excel)
            if st.button("نقل البيانات إلى قاعدة البيانات"):
                # توقع الأعمدة: التاريخ، الفئة، النوع، السعر، الكمية
                for _, row in df_excel.iterrows():
                    # إذا لم يوجد تاريخ في الملف، استخدم تاريخ اليوم
                    date_val = row.get('التاريخ', datetime.now().date())
                    # تحويل التاريخ إلى نص
                    date_val = str(date_val)
                    cat_val = row.get('الفئة', '')
                    type_val = row.get('النوع', '')
                    price_val = row.get('السعر', 0)
                    qty_val = row.get('الكمية', 0)
                    save_row(PRODUCTS_FILE, [date_val, cat_val, type_val, price_val, qty_val])
                add_log(f"استيراد بضاعة من ملف Excel: {excel_file.name}")
                st.success("تم نقل البيانات بنجاح!")
                st.rerun()
        except Exception as e:
            st.error(f"خطأ في قراءة الملف أو نقل البيانات: {e}")

    category = st.text_input("الفئة (مثال: شاحن / سماعة / جراب)")
    type_ = st.text_input("النوع (مثال: typec / a21)")
    price = st.number_input("السعر", min_value=0, value=0, step=1)
    qty = st.number_input("الكمية", min_value=0, value=0, step=1)

    if st.button("➕ إضافة المنتج"):
        save_row(PRODUCTS_FILE, [datetime.now().date(), category, type_, price, qty])
        add_log(f"إضافة منتج: {category} - {type_} - {price} - {qty}")
        st.success("تمت إضافة المنتج ✅")
        
    st.subheader("📋 المخزون")
    products = load_data(PRODUCTS_FILE)

    if not products.empty:
        grouped = products.groupby(["الفئة", "النوع", "السعر"], as_index=False).agg({"الكمية": "sum"})
        for idx, row in grouped.iterrows():
            cat = row['الفئة']
            typ = row['النوع']
            price = row['السعر']
            qty = int(row['الكمية'])
            col1, col2, col3, col4, col5 = st.columns([2,2,2,2,2])
            with col1:
                st.write(f"{cat}")
            with col2:
                st.write(f"{typ}")
            with col3:
                st.write(f"السعر: {price}")
            with col4:
                st.write(f"الكمية: {qty}")
            with col5:
                add_qty = st.number_input("تزويد", min_value=1, value=1, step=1, key=f"add_qty_{idx}")
                reduce_qty = st.number_input("تقليل", min_value=1, value=1, step=1, key=f"reduce_qty_{idx}")
                if st.button("➕ تزويد", key=f"btn_add_{idx}"):
                    save_row(PRODUCTS_FILE, [datetime.now().date(), cat, typ, price, add_qty])
                    add_log(f"تزويد كمية: {cat} - {typ} - {price} +{add_qty}")
                    st.success("تمت إضافة الكمية بنجاح ✅")
                    st.rerun()
                if st.button("➖ تقليل", key=f"btn_reduce_{idx}"):
                    if reduce_qty > qty:
                        st.error("لا يمكن تقليل الكمية أكثر من المتاح!")
                    else:
                        deduct_from_inventory(cat, typ, price, reduce_qty)
                        add_log(f"تقليل كمية: {cat} - {typ} - {price} -{reduce_qty}")
                        st.success("تم تقليل الكمية بنجاح ✅")
                        st.rerun()
        # عرض جدول مجمع بعد الأزرار
        st.markdown("---")
        st.dataframe(grouped, use_container_width=True)
# ==========================
# المكن
# ==========================
elif menu == "المكن":
    st.header("🏧 إدارة المكن")

    machines = ["فوري 1", "فوري 2", "ممكن"]

    # خانة إدخال أرقام حرة منفصلة
    st.subheader("🔢 خانة أرقام حرة (لا ترتبط بأي بيانات)")
    free_number_df = load_data("free_number")
    if not free_number_df.empty and "القيمة" in free_number_df.columns:
        last_value = int(pd.to_numeric(free_number_df.iloc[-1]["القيمة"], errors="coerce"))
    else:
        last_value = 0

    free_number = st.number_input(
        "أدخل أي رقم تريده هنا",
        min_value=-10**12,
        value=last_value,
        step=1,
        key="free_number"
    )

    if st.button("💾 تسجيل الرقم الحر"):
        overwrite_data("free_number", pd.DataFrame({"القيمة": [free_number]}))
        add_log(f"تسجيل رقم حر في صفحة المكن: {free_number}")
        st.success("تم تسجيل الرقم الحر ✅")
        st.rerun()

    # تحميل/تهيئة بيانات الأرصدة اليومية للمكن
    daily_df = load_data(MACHINE_DAILY_FILE)
    expected_cols = ["المكنة", "رصيد الفتح", "رصيد مضاف", "رصيد نهاية"]

    # تأمين الأعمدة المطلوبة
    for c in expected_cols:
        if c not in daily_df.columns:
            daily_df[c] = 0

    if not daily_df.empty:
        daily_df = daily_df[expected_cols]

    if daily_df.empty:
        # أول مرة: أنشئ صف لكل ماكينة
        rows = []
        for m in machines:
            rows.append([m, 0, 0, 0])
        daily_df = pd.DataFrame(rows, columns=expected_cols)
        overwrite_data(MACHINE_DAILY_FILE, daily_df)

    # واجهة إدخال لكل ماكينة (الرصيد ممكن يبقى بالسالب)
    st.subheader("📲 بيانات اليوم لكل ماكينة")
    totals_sold = 0
    edited_df = daily_df.copy()

    for i, row in daily_df.iterrows():
        st.markdown(f"### 💳 {row['المكنة']}")
        c1, c2, c3 = st.columns(3)

        with c1:
            open_balance = st.number_input(
                "رصيد فتح",
                min_value=-10**12,
                value=int(safe_int(row['رصيد الفتح'])),
                step=1,
                key=f"open_{i}"
            )
        with c2:
            added = st.number_input(
                "رصيد مضاف",
                min_value=-10**12,
                value=int(safe_int(row['رصيد مضاف'])),
                step=1,
                key=f"add_{i}"
            )
        with c3:
            end_balance = st.number_input(
                "رصيد نهاية",
                min_value=-10**12,
                value=int(safe_int(row['رصيد نهاية'])),
                step=1,
                key=f"end_{i}"
            )

        sold = int(open_balance) + int(added) - int(end_balance)
        totals_sold += sold
        st.write(f"🧮 المباع (الفلوس في الدُرج من هذه المكنة): **{int(sold)}**")

        edited_df.at[i, 'رصيد الفتح'] = int(open_balance)
        edited_df.at[i, 'رصيد مضاف'] = int(added)
        edited_df.at[i, 'رصيد نهاية'] = int(end_balance)

    # زرار صريح لحفظ حالة الأرصدة اليومية في الجدول
    if st.button("💾 حفظ حالة أرصدة المكن لليوم"):
        overwrite_data(MACHINE_DAILY_FILE, edited_df)
        add_log("حفظ حالة أرصدة المكن لليوم")
        st.success("تم حفظ الأرصدة اليومية للمكن ✅")
        st.rerun()

    # التعامل مع جدول ملخص أيام المكن (MACHINE_DAY_META_FILE)
    today_str = datetime.now().strftime("%Y-%m-%d")
    meta = load_data(MACHINE_DAY_META_FILE)

    meta_expected_cols = [
        "التاريخ",
        "تحصيل الشركة (إجمالي)",
        "فلوس الدُرج قبل التحصيل",
        "فلوس معايا بعد التحصيل",
        "فلوس معايا تراكمي",
    ]

    # تأمين الأعمدة
    for c in meta_expected_cols:
        if c not in meta.columns:
            meta[c] = 0

    if not meta.empty:
        meta = meta[meta_expected_cols]
    else:
        meta = pd.DataFrame(columns=meta_expected_cols)

    # حساب التراكمي السابق (آخر يوم أقل من اليوم)
    prev_cumulative = 0
    if not meta.empty:
        try:
            meta_sorted = meta.sort_values("التاريخ")
            prev_rows = meta_sorted[meta_sorted["التاريخ"] < today_str]
            if not prev_rows.empty:
                prev_cumulative = int(safe_int(prev_rows.iloc[-1]["فلوس معايا تراكمي"]))
        except Exception:
            prev_cumulative = 0

    # سطر اليوم (إن وجد) أو إنشاؤه
    row_today = meta[meta["التاريخ"] == today_str]
    if row_today.empty:
        new_row = pd.DataFrame(
            [[today_str, 0, int(totals_sold), int(totals_sold), int(prev_cumulative + totals_sold)]],
            columns=meta_expected_cols
        )
        meta = pd.concat([meta, new_row], ignore_index=True)
        row_today = new_row

    # قراءة القيم الحالية لليوم
    current_collect = int(safe_int(row_today["تحصيل الشركة (إجمالي)"].iloc[0]))
    current_drawer = int(safe_int(row_today["فلوس الدُرج قبل التحصيل"].iloc[0]))
    current_cash_after = int(safe_int(row_today["فلوس معايا بعد التحصيل"].iloc[0]))
    current_cumulative = int(safe_int(row_today["فلوس معايا تراكمي"].iloc[0]))

    st.markdown("---")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("💰 فلوس الدُرج (إجمالي كل المكن)", int(totals_sold))

    with c2:
        new_collect = st.number_input(
            "🏦 تحصيل الشركة (إجمالي اليوم)",
            min_value=-10**12,
            value=int(current_collect),
            step=1,
            key="collect_total"
        )

    # تهيئة قيمة الفلوس معايا في الـ session_state أول مرة
    if "cash_after" not in st.session_state:
        st.session_state["cash_after"] = int(current_cash_after)

    with c3:
        auto_sync = st.checkbox(
            "تفعيل التحديث التلقائي (فلوس معايا = فلوس الدُرج - تحصيل)",
            value=True,
            key="machine_auto_sync"
        )

        # لو التحديث التلقائي شغال: كل ما تحصيل الشركة أو إجمالي الدرج يتغير
        # نعيد حساب الفلوس معايا ونحطها في السيشن
        if auto_sync:
            st.session_state["cash_after"] = int(totals_sold) - int(new_collect)

        # نعرض القيمة في number_input (وتتحدّث أوتوماتيك مع أي تغيير)
        cash_after_input = st.number_input(
            "💼 الفلوس معايا بعد التحصيل",
            min_value=-10**12,
            value=int(st.session_state["cash_after"]),
            step=1,
            key="cash_after"
        )

    # حساب التراكمي لليوم بناءً على آخر تراكمي قبل اليوم
    today_cumulative = int(prev_cumulative) + int(cash_after_input)

    # تحديث/حفظ سطر اليوم في meta
    meta.loc[meta["التاريخ"] == today_str, "تحصيل الشركة (إجمالي)"] = int(new_collect)
    meta.loc[meta["التاريخ"] == today_str, "فلوس الدُرج قبل التحصيل"] = int(totals_sold)
    meta.loc[meta["التاريخ"] == today_str, "فلوس معايا بعد التحصيل"] = int(cash_after_input)
    meta.loc[meta["التاريخ"] == today_str, "فلوس معايا تراكمي"] = int(today_cumulative)
    overwrite_data(MACHINE_DAY_META_FILE, meta)

    quick_calc_cash_after = int(totals_sold) - int(new_collect)
    st.caption(
        f"الحساب السريع (فلوس الدُرج - تحصيل الشركة) = {int(quick_calc_cash_after)}. "
        f"قيمة 'الفلوس معايا تراكمي' اليوم = {int(today_cumulative)}."
    )

    st.markdown("---")
    if st.button("✅ إنهاء اليوم للمكن"):
        # حفظ سجل اليوم في جدول MACHINE_FILE
        for i, row in edited_df.iterrows():
            open_balance = safe_int(row["رصيد الفتح"])
            added = safe_int(row["رصيد مضاف"])
            end_balance = safe_int(row["رصيد نهاية"])
            sold = int(open_balance) + int(added) - int(end_balance)
            save_row(
                MACHINE_FILE,
                [today_str, row["المكنة"], int(open_balance), int(added), int(end_balance), int(sold)]
            )

        # تجهيز أرصدة اليوم التالي:
        # - رصيد الفتح = رصيد نهاية اليوم الحالي
        # - رصيد المضاف = 0
        # - رصيد النهاية = 0 (زي ما طلبت)
        next_df = pd.DataFrame(columns=expected_cols)
        for _, row in edited_df.iterrows():
            next_df.loc[len(next_df)] = [
                row["المكنة"],
                int(safe_int(row["رصيد نهاية"])),  # رصيد فتح الغد = نهاية اليوم الحالي
                0,                                  # رصيد مضاف الغد
                0,                                  # رصيد نهاية الغد يبدأ بصفر
            ]
        overwrite_data(MACHINE_DAILY_FILE, next_df)

        # إنشاء سطر اليوم التالي في meta لو مش موجود
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        meta_after = load_data(MACHINE_DAY_META_FILE)
        if "التاريخ" not in meta_after.columns:
            meta_after["التاريخ"] = ""
        if tomorrow not in list(meta_after["التاريخ"]):
            save_row(MACHINE_DAY_META_FILE, [tomorrow, 0, 0, int(today_cumulative), int(today_cumulative)])

        add_log(
            f"إنهاء يوم المكن {today_str} | إجمالي مباع {int(totals_sold)} "
            f"| تحصيل الشركة {int(new_collect)} | الفلوس معي اليوم {int(cash_after_input)} "
            f"| الفلوس معايا تراكمي {int(today_cumulative)}"
        )

        st.success(
            "تم إنهاء اليوم وتحويل رصيد النهاية إلى رصيد فتح لليوم الجديد ✅ "
            "(ورصيد نهاية اليوم الجديد يبدأ بصفر، والفلوس معايا تراكمي اتحملت لليوم الجديد)"
        )
        st.rerun()

    st.markdown("---")
    st.subheader("📚 التقرير التفصيلي لحركة المكن (كل عملية يومية)")
    st.dataframe(load_data(MACHINE_FILE), use_container_width=True)

    st.subheader("📊 ملخص أيام المكن (تحصيل إجمالي + فلوس الدُرج + تراكمي)")
    st.dataframe(load_data(MACHINE_DAY_META_FILE), use_container_width=True)
# ==========================
# البيع (اليومي + سجل + ديون/مدفوعات)
# ==========================
elif menu == "البيع":
    st.header("🛒 صفحة البيع اليومي")

    products_all = load_data(PRODUCTS_FILE)
    if products_all is None or products_all.empty:
        st.warning("لا يوجد منتجات في المخزون")
    else:
        products_all['الكمية'] = pd.to_numeric(products_all['الكمية'], errors='coerce').fillna(0)
        products_all['السعر'] = pd.to_numeric(products_all['السعر'], errors='coerce').fillna(0)

        grouped = products_all.groupby(["الفئة", "النوع", "السعر"], as_index=False).agg({"الكمية": "sum"})

        c1, c2, c3 = st.columns(3)
        with c1:
            category = st.selectbox("اختر الفئة", grouped['الفئة'].unique())
        with c2:
            type_options = grouped[grouped['الفئة'] == category]['النوع'].unique()
            type_ = st.selectbox("اختر النوع", type_options)
        with c3:
            price_options = grouped[(grouped['الفئة'] == category) & (grouped['النوع'] == type_)]['السعر'].unique()
            price = st.selectbox("اختر السعر", price_options)

        avail = available_qty(category, type_, price)
        qty = st.number_input("الكمية المباعة", min_value=1, max_value=max(1, int(avail)), value=1, step=1)
        total_sale = int(price) * int(qty)
        st.metric("💵 إجمالي العملية", int(total_sale))

        if st.button("✔️ تسجيل البيع"):
            if qty > available_qty(category, type_, price):
                st.error("الكمية المطلوبة غير متاحة في المخزون")
            else:
                deduct_from_inventory(category, type_, price, int(qty))
                sale_id = next_id(SALES_FILE)
                save_row(SALES_FILE, [sale_id, datetime.now().strftime("%Y-%m-%d"), category, type_, int(price), int(qty), int(total_sale)])
                add_log(f"عملية بيع: {category} - {type_} - {price} × {qty} = {total_sale}")
                st.success("تم تسجيل البيع وتحديث المخزون ✅")
                st.rerun()

    st.divider()
    st.subheader("🧾 مبيعات اليوم (تفصيلي)")
    sales_df = load_data(SALES_FILE)
    ################################################################################################################
    # اختيار تاريخ يدوي
    if not sales_df.empty and 'التاريخ' in sales_df.columns:
        all_days = sorted(sales_df['التاريخ'].unique(), reverse=True)
        default_day = all_days[0]
    else:
        all_days = [date.today().strftime("%Y-%m-%d")]
        default_day = all_days[0]

    picked_day = st.date_input("اختر يوم العرض", value=datetime.strptime(default_day, "%Y-%m-%d").date(),
                               min_value=datetime.strptime(all_days[-1], "%Y-%m-%d").date() if all_days else date.today(),
                               max_value=datetime.strptime(all_days[0], "%Y-%m-%d").date() if all_days else date.today())
    today_str = picked_day.strftime("%Y-%m-%d")
    ###############################################################################################################
    today_sales = sales_df[sales_df['التاريخ'] == today_str].copy() if not sales_df.empty else pd.DataFrame(columns=sales_df.columns)

    if not today_sales.empty:
        today_sales['السعر'] = pd.to_numeric(today_sales['السعر'], errors='coerce').fillna(0)
        today_sales['الكمية'] = pd.to_numeric(today_sales['الكمية'], errors='coerce').fillna(0)
        today_sales['الإجمالي'] = pd.to_numeric(today_sales['الإجمالي'], errors='coerce').fillna(0)
        total_today_sales = int(today_sales['الإجمالي'].sum())
        st.metric("📈 إجمالي مبيعات اليوم", total_today_sales)

        for i, row in today_sales.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])
            with col1: st.write(f"#{int(row['المعرف'])}")
            with col2: st.write(f"{row['الفئة']} / {row['النوع']}")
            with col3: st.write(f"السعر: {int(row['السعر'])}")
            with col4:
                max_qty = available_qty(row['الفئة'], row['النوع'], int(row['السعر'])) + int(row['الكمية'])
                new_qty = st.number_input(
                    "تعديل الكمية",
                    min_value=1,
                    max_value=max(1, int(max_qty)),
                    value=int(row['الكمية']),
                    key=f"edit_sale_qty_{int(row['المعرف'])}",
                    step=1
                )
            with col5:
                if st.button("💾 حفظ", key=f"save_edit_{int(row['المعرف'])}"):
                    old_qty = int(row['الكمية'])
                    delta = int(new_qty) - old_qty
                    if delta != 0:
                        if delta > 0:
                            if delta > available_qty(row['الفئة'], row['النوع'], int(row['السعر'])):
                                st.error("الكمية الإضافية غير متاحة")
                                st.stop()
                            else:
                                deduct_from_inventory(row['الفئة'], row['النوع'], int(row['السعر']), delta)
                                
                        else:
                            add_back_to_inventory(row['الفئة'], row['النوع'], int(row['السعر']), -delta)
                        sales_df.loc[(sales_df['المعرف'] == row['المعرف']) & (sales_df['التاريخ'] == today_str), 'الكمية'] = int(new_qty)
                        sales_df.loc[(sales_df['المعرف'] == row['المعرف']) & (sales_df['التاريخ'] == today_str), 'الإجمالي'] = int(new_qty) * int(row['السعر'])
                        overwrite_data(SALES_FILE, sales_df)
                        add_log(f"تعديل بيع #{int(row['المعرف'])}: كمية {old_qty} → {int(new_qty)}")
                        st.rerun()
            with col6:
                if st.button("🗑️ حذف", key=f"delete_sale_{int(row['المعرف'])}"):
                    add_back_to_inventory(row['الفئة'], row['النوع'], int(row['السعر']), int(row['الكمية']))
                    sales_df = sales_df[~((sales_df['المعرف'] == row['المعرف']) & (sales_df['التاريخ'] == today_str))]
                    overwrite_data(SALES_FILE, sales_df)
                    add_log(f"حذف بيع #{int(row['المعرف'])} وإرجاع الكمية للمخزون")
                    st.rerun()

        st.dataframe(
            sales_df[sales_df['التاريخ'] == today_str][['المعرف','الفئة','النوع','السعر','الكمية','الإجمالي']].reset_index(drop=True),
            use_container_width=True
        )
    else:
        total_today_sales = 0
        st.info("لا توجد مبيعات مُسجلة اليوم حتى الآن")

    st.markdown("---")
    cdebt, cpay = st.columns(2)
        # إضافة ديون مباشرة في الرصيد التراكمي (خارج الديون اليومية)

    st.subheader("إضافة دين  (عليه فلوس)")
    name_perm = st.text_input("اسم الشخص (دين )", key="perm_debt_name")
    amount_perm = st.number_input("المبلغ (دين )", min_value=1, value=1, step=1, key="perm_debt_amount")
    if st.button("➕ إضافة دين ", key="add_perm_debt_btn"):
        if not name_perm.strip():
            st.error("يرجى إدخال اسم الشخص")
        else:
            # أضف أو حدث الرصيد التراكمي
            out_df = _get_outstanding_df()
            if name_perm in list(out_df['الاسم']):
                idx = out_df[out_df['الاسم'] == name_perm].index[0]
                out_df.at[idx, 'الرصيد'] = float(out_df.at[idx, 'الرصيد']) + float(amount_perm)
                overwrite_data(OUTSTANDING_FILE, out_df)
            else:
                save_row(OUTSTANDING_FILE, [name_perm, float(amount_perm)])
            add_log(f"إضافة دين : {name_perm} - {amount_perm}")
            st.success("تمت إضافة الدين  بنجاح ✅")
            st.rerun()

    # إضافة مدفوعات مباشرة في الرصيد التراكمي (خارج المدفوعات اليومية)
    st.subheader("إضافة مدفوع برا ")
    name_perm_pay = st.text_input("اسم الشخص ", key="perm_pay_name")
    amount_perm_pay = st.number_input("المبلغ ", min_value=1, value=1, step=1, key="perm_pay_amount")
    if st.button("➕ إضافة مدفوع ", key="add_perm_pay_btn"):
        if not name_perm_pay.strip():
            st.error("يرجى إدخال اسم الشخص")
        else:
            # أضف أو حدث الرصيد التراكمي (يخصم من الرصيد)
            out_df = _get_outstanding_df()
            if name_perm_pay in list(out_df['الاسم']):
                idx = out_df[out_df['الاسم'] == name_perm_pay].index[0]
                out_df.at[idx, 'الرصيد'] = float(out_df.at[idx, 'الرصيد']) - float(amount_perm_pay)
                if out_df.at[idx, 'الرصيد'] <= 0:
                    out_df = out_df.drop(idx)
                overwrite_data(OUTSTANDING_FILE, out_df)
            else:
                save_row(OUTSTANDING_FILE, [name_perm_pay, -float(amount_perm_pay)])
            add_log(f"إضافة مدفوع : {name_perm_pay} - {amount_perm_pay}")
            st.success("تمت إضافة المدفوع  بنجاح ✅")
            st.rerun()

    out_df = _get_outstanding_df()
    debts_today_df = load_data(DEBTS_DAILY_FILE)
    debts_today_df = debts_today_df[debts_today_df['التاريخ'] == today_str] if not debts_today_df.empty else pd.DataFrame(columns=load_data(DEBTS_DAILY_FILE).columns)
    suggested_names = sorted(list(set(list(out_df['الاسم']) + (list(debts_today_df['الاسم']) if not debts_today_df.empty else []))))

    with cdebt:
        st.subheader("📌 سجل الديون (اليومي)")
        cn1, cn2 = st.columns([2, 1])
        with cn1:
            debtor_pick = st.selectbox("اختر اسم (أو اكتب)", options=[""] + suggested_names, index=0, key="debtor_pick")
            debtor_name = st.text_input("أو اكتب الاسم يدويًا", value="", key="debtor_name_manual")
            final_debtor = debtor_name.strip() if debtor_name.strip() else debtor_pick.strip()
        with cn2:
            debtor_amount = st.number_input("مبلغ الدين", min_value=1, value=1, key="debtor_amount", step=1)
        if st.button("➕ تسجيل دين", key="add_debt_btn"):
            if not final_debtor:
                st.error("من فضلك اختر أو اكتب الاسم")
            else:
                record_daily_debt(final_debtor, float(debtor_amount), today_str)
                st.success("تم تسجيل الدين ✅ — وتم تحديث التراكمي")
                st.rerun()

        debts_today_view = load_data(DEBTS_DAILY_FILE)
        debts_today_view = debts_today_view[debts_today_view['التاريخ'] == today_str] if not debts_today_view.empty else pd.DataFrame(columns=load_data(DEBTS_DAILY_FILE).columns)
        if not debts_today_view.empty:
            debts_today_view['المبلغ'] = pd.to_numeric(debts_today_view['المبلغ'], errors='coerce').fillna(0)
            for i, row in debts_today_view.iterrows():
                d1, d2, d3, d4 = st.columns([3, 3, 2, 2])
                with d1: st.write(f"#{int(row['المعرف'])} — {row['الاسم']}")
                with d2:
                    new_amt = st.number_input("تعديل المبلغ", min_value=1, value=int(row['المبلغ']), key=f"edit_debt_amt_{int(row['المعرف'])}", step=1)
                with d3:
                    if st.button("💾 حفظ", key=f"save_debt_edit_{int(row['المعرف'])}"):
                        delta = int(new_amt) - int(row['المبلغ'])
                        if delta != 0:
                            adjust_outstanding(row['الاسم'], +float(delta))
                            df_all = load_data(DEBTS_DAILY_FILE)
                            df_all.loc[df_all['المعرف'] == row['المعرف'], 'المبلغ'] = int(new_amt)
                            overwrite_data(DEBTS_DAILY_FILE, df_all)
                            add_log(f"تعديل دين #{int(row['المعرف'])}: {int(row['المبلغ'])} → {int(new_amt)}")
                            st.rerun()
                with d4:
                    if st.button("🗑️ حذف", key=f"delete_debt_{int(row['المعرف'])}"):
                        adjust_outstanding(row['الاسم'], -float(row['المبلغ']))
                        df_all = load_data(DEBTS_DAILY_FILE)
                        df_all = df_all[df_all['المعرف'] != row['المعرف']]
                        overwrite_data(DEBTS_DAILY_FILE, df_all)
                        add_log(f"حذف دين #{int(row['المعرف'])}")
                        st.rerun()

        st.markdown("**📚 التراكمي — الرصيد الحالي على الأشخاص**")
        st.dataframe(_get_outstanding_df(), use_container_width=True)

    with cpay:
        st.subheader("💵 سجل المدفوعات (اليومي)")
        cp1, cp2 = st.columns([2, 1])
        with cp1:
            payer_pick = st.selectbox("اختر اسم (أو اكتب)", options=[""] + suggested_names, index=0, key="payer_pick")
            payer_name_manual = st.text_input("أو اكتب الاسم يدويًا", value="", key="payer_name_manual")
            final_payer = payer_name_manual.strip() if payer_name_manual.strip() else payer_pick.strip()
        with cp2:
            payer_amount = st.number_input("مبلغ الدفع", min_value=1, value=1, key="payer_amount", step=1)
        if st.button("➕ تسجيل دفع", key="add_payment_btn"):
            if not final_payer:
                st.error("من فضلك اختر أو اكتب الاسم")
            else:
                record_daily_payment(final_payer, float(payer_amount), today_str)
                st.success("تم تسجيل الدفع ✅ — وتم خصمه من التراكمي (ويبقى ظاهر في سجل اليوم)")
                st.rerun()

        payments_today_view = load_data(PAYMENTS_DAILY_FILE)
        payments_today_view = payments_today_view[payments_today_view['التاريخ'] == today_str] if not payments_today_view.empty else pd.DataFrame(columns=load_data(PAYMENTS_DAILY_FILE).columns)
        if not payments_today_view.empty:
            payments_today_view['المبلغ'] = pd.to_numeric(payments_today_view['المبلغ'], errors='coerce').fillna(0)
            for i, row in payments_today_view.iterrows():
                p1, p2, p3, p4 = st.columns([3, 3, 2, 2])
                with p1: st.write(f"#{int(row['المعرف'])} — {row['الاسم']}")
                with p2:
                    new_amt = st.number_input("تعديل المبلغ", min_value=1, value=int(row['المبلغ']), key=f"edit_pay_amt_{int(row['المعرف'])}", step=1)
                with p3:
                    if st.button("💾 حفظ", key=f"save_pay_edit_{int(row['المعرف'])}"):
                        delta = int(new_amt) - int(row['المبلغ'])
                        if delta != 0:
                            adjust_outstanding(row['الاسم'], -float(delta))
                            df_all = load_data(PAYMENTS_DAILY_FILE)
                            df_all.loc[df_all['المعرف'] == row['المعرف'], 'المبلغ'] = int(new_amt)
                            overwrite_data(PAYMENTS_DAILY_FILE, df_all)
                            add_log(f"تعديل دفع #{int(row['المعرف'])}: {int(row['المبلغ'])} → {int(new_amt)}")
                            st.rerun()
                with p4:
                    if st.button("🗑️ حذف", key=f"delete_pay_{int(row['المعرف'])}"):
                        adjust_outstanding(row['الاسم'], +float(row['المبلغ']))
                        df_all = load_data(PAYMENTS_DAILY_FILE)
                        df_all = df_all[df_all['المعرف'] != row['المعرف']]
                        overwrite_data(PAYMENTS_DAILY_FILE, df_all)
                        add_log(f"حذف دفع #{int(row['المعرف'])}")
                        st.rerun()

    total_debts_today = int(pd.to_numeric(debts_today_df['المبلغ'], errors='coerce').fillna(0).sum()) if not debts_today_df.empty else 0
    total_payments_today = int(pd.to_numeric(payments_today_view['المبلغ'], errors='coerce').fillna(0).sum()) if not payments_today_view.empty else 0

    st.markdown("---")
    st.subheader("📊 الملخص")
    total_today_sales = int(today_sales['الإجمالي'].sum()) if not today_sales.empty else 0
    net_total = int(total_today_sales) + int(total_payments_today) - int(total_debts_today)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("مبيعات اليوم", int(total_today_sales))
    c2.metric("المدفوع اليوم", int(total_payments_today))
    c3.metric("الديون اليوم", int(total_debts_today))
    c4.metric("⚖️ الصافي (مبيعات + دفع - ديون)", int(net_total))

    st.markdown("---")
    if st.button("✅ إنهاء اليوم وإغلاق المبيعات + الديون + المدفوعات"):
        count_today_sales = int(len(today_sales)) if not today_sales.empty else 0
        save_row(SALES_SUMMARY_FILE, [today_str, int(total_today_sales), count_today_sales])
        sales_df = sales_df[sales_df['التاريخ'] != today_str]
        overwrite_data(SALES_FILE, sales_df)

        if not debts_today_df.empty:
            debts_arch = load_data(DEBTS_ARCHIVE_FILE)
            merged = pd.concat([debts_arch, debts_today_df], ignore_index=True) if not debts_arch.empty else debts_today_df
            overwrite_data(DEBTS_ARCHIVE_FILE, merged)
        save_row(DEBTS_DAILY_SUMMARY_FILE, [today_str, int(total_debts_today), int(len(debts_today_df))])
        all_debts_daily = load_data(DEBTS_DAILY_FILE)
        all_debts_daily = all_debts_daily[all_debts_daily['التاريخ'] != today_str]
        overwrite_data(DEBTS_DAILY_FILE, all_debts_daily)

        payments_today_df2 = load_data(PAYMENTS_DAILY_FILE)
        payments_today_df2 = payments_today_df2[payments_today_df2['التاريخ'] == today_str] if not payments_today_df2.empty else pd.DataFrame()
        total_payments_today2 = int(pd.to_numeric(payments_today_df2['المبلغ'], errors='coerce').fillna(0).sum()) if not payments_today_df2.empty else 0
        if not payments_today_df2.empty:
            pays_arch = load_data(PAYMENTS_ARCHIVE_FILE)
            merged_p = pd.concat([pays_arch, payments_today_df2], ignore_index=True) if not pays_arch.empty else payments_today_df2
            overwrite_data(PAYMENTS_ARCHIVE_FILE, merged_p)
        save_row(PAYMENTS_DAILY_SUMMARY_FILE, [today_str, int(total_payments_today2), int(len(payments_today_df2))])
        all_pays_daily = load_data(PAYMENTS_DAILY_FILE)
        all_pays_daily = all_pays_daily[all_pays_daily['التاريخ'] != today_str]
        overwrite_data(PAYMENTS_DAILY_FILE, all_pays_daily)

        add_log(f"إنهاء اليوم {today_str}: مبيعات {int(total_today_sales)} / ديون {int(total_debts_today)} / مدفوع {int(total_payments_today2)}")
        st.success("تم إغلاق اليوم ونقل السجلات للأرشيف/الملخصات — التراكمي (الرصيد) تم تحديثه لحظيًا مع التسجيل ✅")
        st.rerun()

    st.subheader("📚 سجل الأيام السابقة (ملخص المبيعات)")
    st.dataframe(load_data(SALES_SUMMARY_FILE), use_container_width=True)

# ==========================
# التقارير
# ==========================
elif menu == "التقارير":
    st.header("📑 التقارير")

    st.subheader("تقرير الكاش")
    st.dataframe(load_data(CASH_FILE), use_container_width=True)

    st.subheader("تقرير الأشخاص (ليهم/عليهم)")
    st.dataframe(load_data(DEBTS_FILE), use_container_width=True)

    st.subheader("تقرير البضاعة")
    st.dataframe(load_data(PRODUCTS_FILE), use_container_width=True)

    st.subheader("تقرير المكن")
    st.dataframe(load_data(MACHINE_FILE), use_container_width=True)

    st.subheader("تقرير المبيعات (تفصيلي)")
    st.dataframe(load_data(SALES_FILE), use_container_width=True)

    st.subheader("تقرير المبيعات (ملخص يومي)")
    st.dataframe(load_data(SALES_SUMMARY_FILE), use_container_width=True)

    st.subheader("📌 ديون البيع — اليومي")
    st.dataframe(load_data(DEBTS_DAILY_FILE), use_container_width=True)

    st.subheader("📌 ديون البيع — الأرشيف (تراكمي تفصيلي)")
    st.dataframe(load_data(DEBTS_ARCHIVE_FILE), use_container_width=True)

    st.subheader("📌 ديون البيع — الملخص اليومي")
    st.dataframe(load_data(DEBTS_DAILY_SUMMARY_FILE), use_container_width=True)

    st.subheader("📌 الرصيد التراكمي على الأشخاص (Outstanding)")
    st.dataframe(load_data(OUTSTANDING_FILE), use_container_width=True)

    st.subheader("💵 المدفوعات — اليومي")
    st.dataframe(load_data(PAYMENTS_DAILY_FILE), use_container_width=True)

    st.subheader("💵 المدفوعات — الأرشيف (تراكمي تفصيلي)")
    st.dataframe(load_data(PAYMENTS_ARCHIVE_FILE), use_container_width=True)

    st.subheader("💵 المدفوعات — الملخص اليومي")
    st.dataframe(load_data(PAYMENTS_DAILY_SUMMARY_FILE), use_container_width=True)

    st.subheader("📋 سجل التالف")
    st.dataframe(load_data(DAMAGED_FILE), use_container_width=True)

# ==========================
# السجل العام
# ==========================
elif menu == "السجل":
    st.header("📝 السجل")
    st.dataframe(load_data(LOG_FILE), use_container_width=True)

# ==========================
# الأرباح
# ==========================
elif menu == "الأرباح":
    st.header("💰 الأرباح اليومية")
    st.dataframe(load_data(PROFIT_FILE), use_container_width=True)

# ==========================
# صفحة البيع (تالف / مرتجع)
# ==========================
elif menu == "البيع التالف/المرتجع":
    st.header("🔄 إدارة التالف والمرتجع")
    products_all = load_data(PRODUCTS_FILE)
    sales_all = load_data(SALES_FILE)
    all_items = pd.concat([
        products_all[['الفئة', 'النوع', 'السعر']],
        sales_all[['الفئة', 'النوع', 'السعر']]
    ], ignore_index=True).drop_duplicates()
    selected_cat = st.selectbox("اختر الفئة", all_items['الفئة'].unique())
    type_options = all_items[all_items['الفئة'] == selected_cat]['النوع'].unique()
    selected_type = st.selectbox("اختر النوع", type_options)
    price_options = all_items[(all_items['الفئة'] == selected_cat) & (all_items['النوع'] == selected_type)]['السعر'].unique()
    selected_price = st.selectbox("اختر السعر", price_options)
    # الكمية المتاحة للبيع اليوم فقط
    today_str = date.today().strftime("%Y-%m-%d")
    sales_df = load_data(SALES_FILE)
    mask_sale_today = (sales_df['الفئة'] == selected_cat) & (sales_df['النوع'] == selected_type) & (sales_df['السعر'] == selected_price) & (sales_df['التاريخ'] == today_str)
    max_qty = int(sales_df.loc[mask_sale_today, 'الكمية'].sum()) if not sales_df.loc[mask_sale_today].empty else 0
    qty = st.number_input("الكمية المرتجعة أو التالفة", min_value=1, value=1, step=1, max_value=max(1, max_qty))
    st.markdown("**حدد الحالة:**")
    case_type = st.radio("نوع العملية", ["مرتجع", "تالف"])
    same_day = st.checkbox("في نفس يوم البيع؟")
    will_replace = st.checkbox("سيأخذ غيره؟")
    reason = ""
    if case_type == "تالف":
        reason = st.text_input("سبب التالف")
    if will_replace:
        st.markdown("---")
        st.markdown("**اختر المنتج الجديد للاستبدال:**")
        new_cat = st.selectbox("الفئة الجديدة", all_items['الفئة'].unique(), key="new_cat")
        new_type_options = all_items[all_items['الفئة'] == new_cat]['النوع'].unique()
        new_type = st.selectbox("النوع الجديد", new_type_options, key="new_type")
        new_price_options = all_items[(all_items['الفئة'] == new_cat) & (all_items['النوع'] == new_type)]['السعر'].unique()
        new_price = st.selectbox("السعر الجديد", new_price_options, key="new_price")
        # تحقق من الكمية المتاحة للاستبدال
        new_item_qty = available_qty(new_cat, new_type, int(new_price))
        if qty > new_item_qty:
            st.error("الكمية المطلوبة للاستبدال غير متاحة في المخزون!")
    if st.button("تنفيذ العملية"):
        # تحقق من صحة الكمية المرتجعة
        if same_day and case_type == "مرتجع" and qty > max_qty:
            st.error("الكمية المرتجعة أكبر من الكمية المباعة اليوم!")
        else:
            # المرتجع في نفس اليوم: خصم من البيع فقط، وإضافة للمخزون
            if same_day and case_type == "مرتجع":
                if not sales_df.loc[mask_sale_today].empty:
                    sales_df.loc[mask_sale_today, 'الكمية'] = pd.to_numeric(sales_df.loc[mask_sale_today, 'الكمية'], errors='coerce').fillna(0) - qty
                    sales_df.loc[mask_sale_today, 'الإجمالي'] = sales_df.loc[mask_sale_today, 'الكمية'] * int(selected_price)
                    # حذف الصفوف التي أصبحت الكمية فيها <= 0
                    sales_df = sales_df[~(mask_sale_today & (sales_df['الكمية'] <= 0))]
                    overwrite_data(SALES_FILE, sales_df)
                add_back_to_inventory(selected_cat, selected_type, int(selected_price), qty)
                add_log(f"مرتجع في نفس اليوم: {selected_cat} - {selected_type} - {selected_price} - {qty}")
            # التالف في نفس اليوم: لا يؤثر على البيع، فقط يسجل في التالف
            elif same_day and case_type == "تالف":
                save_row(DAMAGED_FILE, [today_str, selected_cat, selected_type, int(selected_price), qty, reason])
                add_log(f"تالف في نفس اليوم: {selected_cat} - {selected_type} - {selected_price} - {qty} - {reason}")
            # المرتجع يوم آخر: إضافة للمخزون فقط
            elif not same_day and case_type == "مرتجع":
                add_back_to_inventory(selected_cat, selected_type, int(selected_price), qty)
                add_log(f"مرتجع يوم آخر: {selected_cat} - {selected_type} - {selected_price} - {qty}")
            # التالف يوم آخر: يسجل في التالف فقط
            elif not same_day and case_type == "تالف":
                save_row(DAMAGED_FILE, [today_str, selected_cat, selected_type, int(selected_price), qty, reason])
                add_log(f"تالف يوم آخر: {selected_cat} - {selected_type} - {selected_price} - {qty} - {reason}")
            # الاستبدال: إضافة بيع جديد وخصم من المخزون للمنتج الجديد فقط
            if will_replace and qty <= available_qty(new_cat, new_type, int(new_price)):
                sale_id_new = next_id(SALES_FILE)
                save_row(SALES_FILE, [sale_id_new, today_str, new_cat, new_type, int(new_price), qty, int(new_price)*int(qty)])
                deduct_from_inventory(new_cat, new_type, int(new_price), qty)
                add_log(f"استبدال بنوع آخر: {selected_cat} - {selected_type} - {selected_price} -> {new_cat} - {new_type} - {new_price} - {qty}")
            st.success("تمت العملية بنجاح")
            st.rerun()
    st.markdown("---")
    st.subheader("📋 سجل التالف والمرتجع")
    damaged_df = load_data(DAMAGED_FILE)
    st.markdown("**سجل التالف:**")
    st.dataframe(damaged_df.tail(20), use_container_width=True)
    log_df = load_data(LOG_FILE)
    returned_logs = log_df[log_df['العملية'].str.contains('مرتجع', na=False)]
    st.markdown("**سجل المرتجع:**")
    st.dataframe(returned_logs.tail(20), use_container_width=True)


# ==========================
# مراجعة المبيعات والمخزون
# ==========================
elif menu == "مراجعة المبيعات والمخزون":
    st.header("📋 مراجعة المبيعات من سجل العمليات (logs)")
    log_df = load_data(LOG_FILE)
    products_df = load_data(PRODUCTS_FILE)
    # استخراج كل عمليات البيع من السجل
    sales_logs = log_df[log_df['العملية'].str.startswith('عملية بيع:')].copy() if not log_df.empty else pd.DataFrame(columns=['التاريخ والوقت','العملية'])
    if sales_logs.empty:
        st.info("لا توجد عمليات بيع مسجلة في السجل.")
    else:
        # استخراج بيانات البيع من نص العملية
        import re
        def parse_sale(log_str):
            # مثال: عملية بيع: شاحن - typec - 100 × 2 = 200
            m = re.search(r'عملية بيع: (.*?) - (.*?) - (.*?) × (.*?) = (.*?)$', log_str)
            if m:
                try:
                    return {
                        'الفئة': m.group(1),
                        'النوع': m.group(2),
                        'السعر': int(float(m.group(3))),
                        'الكمية': int(float(m.group(4))),
                        'الإجمالي': int(float(m.group(5)))
                    }
                except Exception:
                    return None
                
            return None
        sales_data = [parse_sale(x) for x in sales_logs['العملية']]
        sales_data = [x for x in sales_data if x]
        if not sales_data:
            st.info("لم يتم العثور على عمليات بيع قابلة للاستخراج من السجل.")
        else:
            sales_df = pd.DataFrame(sales_data)
            # تجميع إجمالي المباع لكل منتج
            sales_grouped = sales_df.groupby(["الفئة", "النوع", "السعر"], as_index=False).agg({"الكمية": "sum", "الإجمالي": "sum"})
            sales_grouped = sales_grouped.rename(columns={"الكمية": "إجمالي المباع", "الإجمالي": "إجمالي المبيعات"})
            # الكمية الحالية في المخزون
            if not products_df.empty:
                stock_grouped = products_df.groupby(["الفئة", "النوع", "السعر"], as_index=False).agg({"الكمية": "sum"})
                stock_grouped = stock_grouped.rename(columns={"الكمية": "المخزون الحالي"})
            else:
                stock_grouped = pd.DataFrame(columns=["الفئة", "النوع", "السعر", "المخزون الحالي"])
            # دمج الجدولين
            merged = pd.merge(sales_grouped, stock_grouped, on=["الفئة", "النوع", "السعر"], how="left")
            merged["المخزون الحالي"] = merged["المخزون الحالي"].fillna(0).astype(int)
            st.dataframe(merged, use_container_width=True)
            st.caption("جدول مراجعة: كل عمليات البيع من سجل العمليات (logs) مع الكمية المتبقية في المخزون.")
