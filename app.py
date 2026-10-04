import streamlit as st
import pandas as pd
from datetime import date, datetime
import styles
import util
import storage as STORAGE
import analytics

# ---------------------------------------------------------------------------
# 1) التهيئة العامة وإعدادات الصفحة
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="نظام متابعة شاحنات الصندوق",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تطبيق الأنماط المخصصة (CSS)
styles.apply_custom_css()

# ---------------------------------------------------------------------------
# 2) الثوابت والبيانات التعريفية للأقسام
# ---------------------------------------------------------------------------
TODAY = date.today()

SECTIONS = [
    "لوحة التحكم",
    "الحركة اليومية",
    "إدارة السجلات",
    "دورات الزيت والصيانة",
    "التقارير والتحليلات",
    "الإعدادات والنظام"
]

SECTION_META = {
    "dashboard": {"title": "لوحة التحكم", "subtitle": "متابعة المالي والحركة ونسب استهلاك الزيت للأسطول"},
    "daily": {"title": "الحركة اليومية", "subtitle": "تسجيل كشوفات الحركة اليومية والإدخال السريع"},
    "records": {"title": "إدارة السجلات", "subtitle": "عرض وأرشيف جميع البيانات المخزنة والتصفية"},
    "oil": {"title": "دورات الزيت والصيانة", "subtitle": "سجل دورات تغيير الزيت المكتملة وتصفير العدادات"},
    "analytics": {"title": "التقارير والتحليلات", "subtitle": "رسوم بيانية وتحليلات استهلاك الأسطول"},
    "settings": {"title": "الإعدادات والنظام", "subtitle": "التحكم بحدود الزيت، المعاملات ومزامنة البيانات"}
}

ALL_COLUMNS = ["التاريخ", "رقم السيارة", "عدد الزفات", "تفاصيل الزفات", "المسافة المقطوعة (كم)", "الوقت المستغرق"]

# ---------------------------------------------------------------------------
# 3) إدارة حالة الجلسة (Session State)
# ---------------------------------------------------------------------------
if "fleet_data" not in st.session_state:
    st.session_state.fleet_data = STORAGE.load_data()

if "settings" not in st.session_state:
    st.session_state.settings = STORAGE.load_settings()

if "delete_undo_stack" not in st.session_state:
    st.session_state.delete_undo_stack = []

if "flash_message" not in st.session_state:
    st.session_state.flash_message = None

if "current_section" not in st.session_state:
    st.session_state.current_section = SECTIONS[0]

OIL_LIMIT = st.session_state.settings.get("oil_limit", 2500.0)
OIL_FACTOR = st.session_state.settings.get("oil_factor", 1.0)

# ---------------------------------------------------------------------------
# 4) الدوال المساعدة (Helper Functions)
# ---------------------------------------------------------------------------
def flash(msg_type, text):
    st.session_state.flash_message = (msg_type, text)

def display_flash():
    if st.session_state.flash_message:
        mtype, mtext = st.session_state.flash_message
        if mtype == "success":
            st.success(mtext)
        elif mtype == "error":
            st.error(mtext)
        elif mtype == "warning":
            st.warning(mtext)
        st.session_state.flash_message = None

def reload_from_storage():
    try:
        st.session_state.fleet_data = STORAGE.load_data(force_reload=True)
        return True
    except Exception as e:
        st.error(f"خطأ في تحديث البيانات: {e}")
        return False

def add_batch(new_rows, dedup=False):
    try:
        res = STORAGE.add_records(new_rows, dedup=dedup)
        st.session_state.fleet_data = STORAGE.load_data(force_reload=True)
        return res
    except Exception as e:
        return {"error": str(e)}

def undo_last_delete():
    if st.session_state.delete_undo_stack:
        last_deleted = st.session_state.delete_undo_stack.pop()
        STORAGE.add_records(last_deleted)
        st.session_state.fleet_data = STORAGE.load_data(force_reload=True)
        return len(last_deleted)
    return 0

def close_cycle(plate_no, close_date, note=""):
    res = STORAGE.close_oil_cycle(plate_no, close_date, note, OIL_LIMIT)
    st.session_state.fleet_data = STORAGE.load_data(force_reload=True)
    return res

def fleet_overview():
    df = st.session_state.fleet_data
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["رقم السيارة", "إجمالي المسافة (كم)", "إجمالي الزفات", "المسافة الحالية للزيت (كم)", "نسبة استهلاك الزيت (%)"])
    
    grouped = []
    for plate, group in df.groupby("رقم السيارة"):
        total_km = group["المسافة المقطوعة (كم)"].sum()
        total_zfat = group["عدد الزفات"].sum()
        
        oil_logs = STORAGE.load_oil_logs()
        last_oil_date = None
        if len(oil_logs) > 0 and "رقم السيارة" in oil_logs.columns:
            p_logs = oil_logs[oil_logs["رقم السيارة"].astype(str) == str(plate)]
            if len(p_logs) > 0 and "تاريخ التغيير" in p_logs.columns:
                last_oil_date = p_logs["تاريخ التغيير"].max()
        
        if last_oil_date:
            group_since = group[group["التاريخ"] > last_oil_date]
            km_since = group_since["المسافة المقطوعة (كم)"].sum()
        else:
            km_since = total_km

        oil_pct = min(100.0, (km_since / OIL_LIMIT) * 100) if OIL_LIMIT > 0 else 0.0

        grouped.append({
            "رقم السيارة": str(plate),
            "إجمالي المسافة (كم)": round(total_km, 2),
            "إجمالي الزفات": int(total_zfat),
            "المسافة الحالية للزيت (كم)": round(km_since, 2),
            "نسبة استهلاك الزيت (%)": round(oil_pct, 1)
        })

    res_df = pd.DataFrame(grouped)
    if not res_df.empty:
        res_df.sort_values(by="رقم السيارة", key=lambda col: col.map(util.plate_sort_key), inplace=True)
    return res_df

def show_table(df, cols=None):
    if cols:
        disp_cols = [c for c in cols if c in df.columns]
        st.dataframe(df[disp_cols], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# 5) الشريط الجانبي والتنقل (Sidebar & Navigation)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/garbage-truck.png", width=80)
    st.title("صندوق النظافة والتحسين")
    st.caption("نظام إدارة ومتابعة حركة الشاحنات")
    st.divider()

    selected = st.radio(
        "📋 القائمة الرئيسية",
        SECTIONS,
        index=SECTIONS.index(st.session_state.current_section)
    )
    st.session_state.current_section = selected

    st.divider()
    st.caption(f"⚙️ حد الزيت الافتراضي: **{OIL_LIMIT:,.0f} كم**")
    st.caption(f"📅 التاريخ: **{TODAY.strftime('%Y-%m-%d')}**")

display_flash()

# ---------------------------------------------------------------------------
# 6) القسم الأول: لوحة التحكم (Dashboard)
# ---------------------------------------------------------------------------
def page_dashboard():
    st.markdown(styles.header(
        SECTION_META["dashboard"]["title"], SECTION_META["dashboard"]["subtitle"]),
        unsafe_allow_html=True)

    overview = fleet_overview()
    df = st.session_state.fleet_data

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("إجمالي السيارات المسجلة", f"{len(overview)} شاحنة")
    with c2:
        total_km = df["المسافة المقطوعة (كم)"].sum() if df is not None and len(df) > 0 else 0
        st.metric("إجمالي المسافات المقطوعة", f"{total_km:,.1f} كم")
    with c3:
        total_zfat = df["عدد الزفات"].sum() if df is not None and len(df) > 0 else 0
        st.metric("إجمالي عدد الزفات", f"{int(total_zfat):,} زفة")
    with c4:
        overdue = overview[overview["المسافة الحالية للزيت (كم)"] >= OIL_LIMIT] if len(overview) > 0 else []
        st.metric("سيارات تتطلب تغيير الزيت", f"{len(overdue)} شاحنة")

    st.divider()
    st.subheader("🚛 حالة أسطول الشاحنات ونسب الزيت")
    if len(overview) > 0:
        show_table(overview)
    else:
        st.info("لا توجد بيانات مسجلة في النظام حتى الآن.")

# ---------------------------------------------------------------------------
# 7) القسم الثاني: الحركة اليومية (Daily Activity)
# ---------------------------------------------------------------------------
def page_daily():
    st.markdown(styles.header(
        SECTION_META["daily"]["title"], SECTION_META["daily"]["subtitle"]),
        unsafe_allow_html=True)

    entry_date = st.date_input("تاريخ التسجيل", TODAY)

    st.subheader("📋 رفع كشف الحركة (ملف Excel / CSV)")
    uploaded_file = st.file_uploader("اختر ملف الكشف اليومي", type=["xlsx", "xls", "csv"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df_up = pd.read_csv(uploaded_file)
            else:
                df_up = pd.read_excel(uploaded_file)

            st.write("معاينة البيانات المرفوعة:")
            st.dataframe(df_up.head())

            if st.button("📥 استيراد البيانات وحفظها", type="primary"):
                parsed_rows = util.parse_imported_df(df_up, entry_date)
                if parsed_rows:
                    res = add_batch(parsed_rows)
                    if res.get("error"):
                        st.error(f"حدث خطأ أثناء الحفظ: {res['error']}")
                    else:
                        flash("success", f"تم استيراد {len(parsed_rows)} سجل بنجاح.")
                        st.rerun()
                else:
                    st.error("تعذر تعيين الأعمدة بالشكل الصحيح. تأكد من تنسيق الملف.")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")

    st.divider()
    st.subheader("➕ إدخال يدوي سريع")
    with st.form("manual_entry", clear_on_submit=True):
        m1, m2, m3 = st.columns(3)
        with m1:
            plate_manual = st.text_input("رقم السيارة", placeholder="مثال: 12")
            zfat_manual = st.number_input("عدد الزفات", min_value=0, value=1, step=1)
        with m2:
            km_manual = st.number_input("المسافة المقطوعة (كم)", min_value=0.0, value=0.0, step=1.0)
            time_manual = st.text_input("الوقت المستغرق", placeholder="مثال: 5 ساعات أو من 7 إلى 12")
        with m3:
            details_manual = st.text_area("تفاصيل الزفات", placeholder="مثال: حي السلام، السوق المركزية، المستشفى")
            submit_manual = st.form_submit_button("💾 حفظ السجل اليدوي", type="primary", use_container_width=True)

        if submit_manual:
            if not plate_manual.strip():
                st.warning("⚠️ يرجى إدخال رقم السيارة.")
            elif km_manual <= 0:
                st.warning("⚠️ يرجى إدخال مسافة مقطوعة أكبر من صفر.")
            else:
                row_manual = {
                    "التاريخ": entry_date.isoformat(),
                    "رقم السيارة": plate_manual.strip(),
                    "عدد الزفات": int(zfat_manual),
                    "تفاصيل الزفات": details_manual.strip() if details_manual.strip() else "غير محدد",
                    "المسافة المقطوعة (كم)": float(km_manual),
                    "الوقت المستغرق": time_manual.strip() if time_manual.strip() else "غير محدد",
                }
                res = add_batch([row_manual], dedup=False)
                if res.get("error"):
                    st.error(f"❌ حدث خطأ أثناء الحفظ: {res['error']}")
                else:
                    flash("success", f"✅ تم حفظ السجل اليدوي للسيارة {plate_manual} بنجاح.")
                    st.rerun()

# ---------------------------------------------------------------------------
# 8) القسم الثالث: إدارة السجلات والأرشيف (Records & Archive)
# ---------------------------------------------------------------------------
def page_records():
    st.markdown(styles.header(
        SECTION_META["records"]["title"], SECTION_META["records"]["subtitle"]),
        unsafe_allow_html=True)
    
    df = st.session_state.fleet_data
    if df is None or len(df) == 0:
        st.info("لا توجد سجلات محفوظة حتى الآن.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        unique_plates = sorted(df["رقم السيارة"].dropna().astype(str).unique().tolist(), key=util.plate_sort_key)
        plates = ["الكل"] + unique_plates
        selected_plate = st.selectbox("تصفية حسب السيارة", plates)
    with c2:
        try:
            dates = pd.to_datetime(df["التاريخ"]).dt.date
            min_date, max_date = dates.min(), dates.max()
        except Exception:
            min_date, max_date = TODAY, TODAY
        date_range = st.date_input("نطاق التاريخ", value=(min_date, max_date))
    with c3:
        search_term = st.text_input("بحث نصي في التفاصيل", placeholder="اسم الحي أو المنطقة...")

    filtered = df.copy()
    if selected_plate != "الكل":
        filtered = filtered[filtered["رقم السيارة"].astype(str) == selected_plate]
    
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
        parsed_dates = pd.to_datetime(filtered["التاريخ"]).dt.date
        filtered = filtered[(parsed_dates >= start_d) & (parsed_dates <= end_d)]

    if search_term.strip():
        filtered = filtered[filtered["تفاصيل الزفات"].astype(str).str.contains(search_term, case=False, na=False)]

    st.caption(f"عرض {len(filtered)} سجل من أصل {len(df)}")
    show_table(filtered, ALL_COLUMNS)

    st.divider()
    c_undo, _ = st.columns([1, 2])
    with c_undo:
        if st.button("↩️ تراجع عن آخر حذف", disabled=not st.session_state.delete_undo_stack, use_container_width=True):
            count = undo_last_delete()
            flash("success", f"تمت استعادة {count} سجل محذوف بنجاح.")
            st.rerun()

# ---------------------------------------------------------------------------
# 9) القسم الرابع: إدارة دورات الزيت والصيانة (Oil Cycles)
# ---------------------------------------------------------------------------
def page_oil():
    st.markdown(styles.header(
        SECTION_META["oil"]["title"], SECTION_META["oil"]["subtitle"]),
        unsafe_allow_html=True)
    
    st.subheader("🛢️ تغيير الزيت المباشر وإغلاق الدورة")
    overview = fleet_overview()
    if len(overview) == 0:
        st.info("لا توجد سيارات مسجلة في النظام.")
        return

    plates = overview["رقم السيارة"].tolist()
    col1, col2 = st.columns(2)
    with col1:
        sel_plate = st.selectbox("اختر رقم السيارة لتغيير الزيت", plates)
    with col2:
        note = st.text_input("ملاحظة إغلاق الدورة", value="تم تغيير الزيت واعتماد دورة جديدة")

    if st.button("✅ تسجيل تغيير الزيت وبدء دورة جديدة", type="primary"):
        close_cycle(sel_plate, TODAY.isoformat(), note)
        flash("success", f"تم إغلاق دورة السيارة {sel_plate} بنجاح وبدأت دورة جديدة من الصفر.")
        st.rerun()

    st.divider()
    st.subheader("📜 سجل تغييرات الزيت المكتملة")
    try:
        oil_logs = STORAGE.load_oil_logs()
        if len(oil_logs) > 0:
            show_table(oil_logs)
        else:
            st.info("لا يوجد سجل سابق لتغييرات الزيت حتى الآن.")
    except Exception as exc:
        st.error(f"تعذّر تحميل سجل تغييرات الزيت: {exc}")

# ---------------------------------------------------------------------------
# 10) القسم الخامس: التقارير والتحليلات (Analytics)
# ---------------------------------------------------------------------------
def page_analytics():
    st.markdown(styles.header(
        SECTION_META["analytics"]["title"], SECTION_META["analytics"]["subtitle"]),
        unsafe_allow_html=True)
    analytics.render_analytics_dashboard(st.session_state.fleet_data)

# ---------------------------------------------------------------------------
# 11) القسم السادس: الإعدادات والنظام (Settings)
# ---------------------------------------------------------------------------
def page_settings():
    st.markdown(styles.header(
        SECTION_META["settings"]["title"], SECTION_META["settings"]["subtitle"]),
        unsafe_allow_html=True)

    st.subheader("⚙️ إعدادات حد تغيير الزيت والمعاملات")
    with st.form("settings_form"):
        new_limit = st.number_input("حد تغيير الزيت الافتراضي (كم)", value=OIL_LIMIT, step=500.0)
        new_factor = st.number_input("معامل احتساب المسافة (Oil Factor)", value=OIL_FACTOR, step=0.1)
        save_btn = st.form_submit_button("💾 حفظ الإعدادات", type="primary")
        
        if save_btn:
            st.session_state.settings["oil_limit"] = float(new_limit)
            st.session_state.settings["oil_factor"] = float(new_factor)
            STORAGE.save_settings(st.session_state.settings)
            flash("success", "تم حفظ الإعدادات بنجاح.")
            st.rerun()

    st.divider()
    st.subheader("🔄 إدارة مزامنة البيانات")
    if st.button("🔄 إعادة تحديث البيانات من قاعدة البيانات", use_container_width=True):
        if reload_from_storage():
            flash("success", "تم إفراغ الذاكرة المؤقتة وتحديث البيانات بنجاح.")
            st.rerun()

# ---------------------------------------------------------------------------
# 12) توجيه التنقل والصفحات الرئيسية (Router)
# ---------------------------------------------------------------------------
PAGES = {
    SECTION_META["dashboard"]["title"]: page_dashboard,
    SECTION_META["daily"]["title"]: page_daily,
    SECTION_META["records"]["title"]: page_records,
    SECTION_META["oil"]["title"]: page_oil,
    SECTION_META["analytics"]["title"]: page_analytics,
    SECTION_META["settings"]["title"]: page_settings,
}

current_sec = st.session_state.get("current_section", SECTIONS[0])
page_function = PAGES.get(current_sec, page_dashboard)
page_function()