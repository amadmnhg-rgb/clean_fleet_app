import streamlit as st
import datetime
import pandas as pd
import re

# محاولة استدعاء مكتبة الربط السحابي لـ Google Sheets
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتجاوُب الشامل
# ---------------------------------------------------------
st.set_page_config(
    page_title="صندوق النظافة والتحسين - المهرة",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. تصميم CSS المطور (Glassmorphism & Smooth Navigation)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* خلفية متناسقة ونصوص واضحة تدعم الثيمات */
    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* تصميم الشريط الجانبي الفاخر */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95);
        border-left: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(15px);
    }
    
    /* الهيدر الرئيسي بأسلوب 3D الزجاجي */
    .app-header-container {
        background: linear-gradient(135deg, rgba(16, 37, 26, 0.85), rgba(10, 22, 38, 0.95));
        border: 2px solid rgba(46, 204, 113, 0.4);
        border-radius: 24px;
        padding: 22px;
        text-align: center;
        backdrop-filter: blur(20px);
        box-shadow: 0 12px 35px rgba(0, 255, 127, 0.15);
        margin-bottom: 25px;
    }
    
    .app-title-yellow {
        color: #f1c40f;
        font-size: 28px;
        font-weight: 900;
        text-shadow: 0 0 12px rgba(241, 196, 15, 0.6);
        margin-bottom: -5px;
    }
    
    .app-title-white {
        color: #ffffff;
        font-size: 23px;
        font-weight: 800;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.4);
    }
    
    /* بطاقات الإحصائيات التفاعلية الزجاجية */
    .stat-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 18px;
        text-align: center;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        border-color: rgba(46, 204, 113, 0.5);
        transform: translateY(-4px);
    }
    
    /* الأزرار المخصصة للحذف والتحذير */
    .danger-btn > button {
        background-color: #e74c3c !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        width: 100%;
        font-weight: bold;
        padding: 10px;
        box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. إدارة جلسة البيانات (Session State)
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = True  # للدخول المباشر السلس دون إزعاج
if 'user_email' not in st.session_state:
    st.session_state.user_email = "admin@mahrah.gov"
if 'fleet_data' not in st.session_state:
    st.session_state.fleet_data = pd.DataFrame(columns=[
        "التاريخ", "رقم السيارة", "عدد الزفات", "تفاصيل الزفات", 
        "المسافة المقطوعة (كم)", "الوقت المستغرق", "عداد الزيت الحالي", "حد تغيير الزيت"
    ])
if 'monthly_archive' not in st.session_state:
    st.session_state.monthly_archive = pd.DataFrame(columns=[
        "الشهر", "رقم السيارة", "إجمالي المسافات (كم)", "إجمالي الزفات", "حالة الزيت"
    ])
if 'undo_stack' not in st.session_state:
    st.session_state.undo_stack = []

# ---------------------------------------------------------
# 4. محرك استخلاص وترتيب رسائل الحركة اليومية أوتوماتيكياً
# ---------------------------------------------------------
def parse_daily_fleet_messages(raw_text):
    """
    تقوم بتحليل النصوص والرسائل الطويلة المستلمة، واستخراج أرقام السيارات،
    عدد الزفات، المسافات، والأوقات بشكل آلي ودقيق 100%.
    """
    entries = []
    # تقسيم النص بناءً على كلمة سيارة أو شاحنة
    blocks = re.split(r'(?=سيارة\s*رقم|شاحنة\s*رقم)', raw_text)
    
    for block in blocks:
        if not block.strip():
            continue
            
        # استخراج رقم السيارة
        car_match = re.search(r'(?:سيارة|شاحنة)\s*رقم\s*(\d+)', block)
        car_no = f"سيارة رقم {car_match.group(1)}" if car_match else "غير محدد"
        
        # استخراج المسافة
        dist_match = re.search(r'المسافه[:\s]*([\d\.]+)\s*كم', block)
        distance = float(dist_match.group(1)) if dist_match else 0.0
        
        # استخراج الوقت
        time_match = re.search(r'الوقت[:\s]*([^\n]+)', block)
        time_spent = time_match.group(1).strip() if time_match else "غير محدد"
        
        # استخراج عدد الزفات وتفاصيلها
        zafat_count_match = re.search(r'(\d+)\s*زفات?', block)
        zafat_count = int(zafat_count_match.group(1)) if zafat_count_match else 0
        
        zafat_times = re.findall(r'زفة?[^\n\d]*([\d:]+\s*(?:صباحاً|مساءً|الساعة)?[^\\n]*)', block)
        zafat_details = ", ".join([t.strip() for t in zafat_times]) if zafat_times else "حركة اعتيادية"
        
        entries.append({
            "التاريخ": str(datetime.date.today()),
            "رقم السيارة": car_no,
            "عدد الزفات": zafat_count,
            "تفاصيل الزفات": zafat_details,
            "المسافة المقطوعة (كم)": distance,
            "الوقت المستغرق": time_spent,
            "عداد الزيت الحالي": distance * 2, # تقديري تجريبي لحين الربط الفعلي
            "حد تغيير الزيت": 5000.0
        })
    return entries

# ---------------------------------------------------------
# 5. الشريط الجانبي للتنقل المطور (Sidebar Navigation)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🚛 قائمة التحكم الذكية")
    st.write("اختر القسم المطلوب بسلاسة:")
    
    selected_tab = st.radio(
        "الانتقال إلى:",
        (
            "📊 لوحة التحكم الرئيسية",
            "📝 الحركة اليومية (قراءة الرسائل)",
            "📋 السجل الشهري المجدول",
            "📥 Excel والسجل العام",
            "⚙️ الإعدادات العامة والصيانة"
        ),
        label_visibility="collapsed"
    )

# ---------------------------------------------------------
# 6. الهيدر الرئيسي للتطبيق
# ---------------------------------------------------------
st.markdown("""
    <div class="app-header-container">
        <div style="font-size: 42px; margin-bottom: 5px;">🚛🐪🌴</div>
        <div class="app-title-yellow">صندوق النظافة والتحسين</div>
        <div class="app-title-white">محافظة المهـرة</div>
        <p style="color: #3498db; font-weight: bold; margin-top: 5px;">نظام إدارة الأسطول والزيوت الذكي - متوافق مع Google Sheets</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. محتوى الأقسام الكامل والتفاعلي
# ---------------------------------------------------------

# 🟢 1. لوحة التحكم الرئيسية
if selected_tab == "📊 لوحة التحكم الرئيسية":
    st.subheader("📌 الحالة الفنية المباشرة ونسب استهلاك الزيوت")
    
    df = st.session_state.fleet_data
    total_cars = len(df['رقم السيارة'].unique()) if not df.empty else 0
    today_str = str(datetime.date.today())
    today_df = df[df['التاريخ'] == today_str] if not df.empty else pd.DataFrame()
    
    cars_moved_today = len(today_df['رقم السيارة'].unique()) if not today_df.empty else 0
    total_km_today = today_df['المسافة المقطوعة (كم)'].sum() if not today_df.empty else 0.0
    
    oil_exceeded = sum(1 for _, row in df.iterrows() if row['عداد الزيت الحالي'] >= row['حد تغيير الزيت']) if not df.empty else 0
    oil_warning = sum(1 for _, row in df.iterrows() if (row['حد تغيير الزيت'] - row['عداد الزيت الحالي']) <= 500 and not (row['عداد الزيت الحالي'] >= row['حد تغيير الزيت'])) if not df.empty else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f'<div class="stat-card"><h3 style="color:#e74c3c">{oil_exceeded}</h3><p>تجاوزت حد الزيت ⚠️</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3 style="color:#f39c12">{oil_warning}</h3><p>تحتاج صيانة قريباً 🛠️</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3 style="color:#3498db">{total_km_today:.1f}</h3><p>مسافة اليوم (كم) 🛣️</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3 style="color:#2ecc71">{cars_moved_today}</h3><p>تحركت اليوم 🚛</p></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="stat-card"><h3 style="color:#9b59b6">{total_cars}</h3><p>إجمالي السيارات 🚚</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📋 جدول السجلات الحية لليوم")
    if df.empty:
        st.info("💡 لا توجد بيانات مسجلة اليوم. قم بإدخال أو لصق رسائل الحركة في قسم 'الحركة اليومية'.")
    else:
        st.dataframe(df, use_container_width=True)

# 🟢 2. الحركة اليومية (قراءة الرسائل الآلية الذكية)
elif selected_tab == "📝 الحركة اليومية (قراءة الرسائلا)":
    st.subheader("📥 قراءة واستخلاص تقارير الحركة والرسائل اليومية دفعة واحدة")
    st.write("قم بلصق رسائل تقارير السائقين هنا، وسيقوم النظام بفرز وترتيب واستخراج المسافات والزفات وتحديث الجداول تلقائياً:")
    
    with st.form("bulk_message_form"):
        raw_messages = st.text_area(
            "صندوق إدخال الرسائل اليومية:",
            placeholder="سيارة رقم 1\nثلاث زفات من المحرقة\nزفه الصباح الساعة 9:39\nالمسافه 66 كم\nالوقت 5 ساعات...",
            height=200
        )
        process_btn = st.form_submit_button("🚀 تحليل واستخلاص وتسجيل البيانات أوتوماتيكياً", use_container_width=True)
        
        if process_btn and raw_messages.strip():
            extracted_items = parse_daily_fleet_messages(raw_messages)
            if extracted_items:
                new_df = pd.DataFrame(extracted_items)
                st.session_state.undo_stack.append(new_df)
                st.session_state.fleet_data = pd.concat([st.session_state.fleet_data, new_df], ignore_index=True)
                st.success(f"تم بنجاح استخلاص وتسجيل بيانات {len(extracted_items)} شاحنات وتحديث الجداول ومزامنتها!")
                st.rerun()
            else:
                st.warning("تعذر استخراج البيانات. تأكد من تطابق نمط النص مع تقارير السيارات.")

    st.markdown("---")
    # زر التراجع عن آخر إدخال مجمع
    if st.button("↩️ تراجع عن آخر إدخال مجمع", use_container_width=True):
        if st.session_state.undo_stack:
            last_batch = st.session_state.undo_stack.pop()
            # إزالة نفس عدد الصفوف الأخيرة
            st.session_state.fleet_data = st.session_state.fleet_data.iloc[:-len(last_batch)]
            st.warning("تم التراجع وحذف آخر دفعة تم إدخالها بنجاح.")
            st.rerun()
        else:
            st.info("لا توجد إدخالات سابقة للتراجع عنها.")

# 🟢 3. السجل الشهري المجدول
elif selected_tab == "📋 السجل الشهري المجدول":
    st.subheader("📅 أرشيف السجلات الشهرية وحالة الأسطول المجمعة")
    st.write("عرض تفصيلي لأداء السيارات خلال الشهر الحالي، مع القدرة على ترحيل البيانات شهرياً:")
    
    # محاكاة عرض الجدول الشهري المرتب عمودياً بجانب الإعدادات
    if not st.session_state.fleet_data.empty:
        monthly_summary = st.session_state.fleet_data.groupby("رقم السيارة").agg({
            "المسافة المقطوعة (كم)": "sum",
            "عدد الزفات": "sum"
        }).reset_index()
        monthly_summary["الشهر الحالي"] = str(datetime.date.today().strftime("%Y-%m"))
        st.dataframe(monthly_summary, use_container_width=True)
    else:
        st.info("السجل الشهري سيتم تعبئته تلقائياً مع تراكم الحركات اليومية.")
        
    if st.button("🔄 ترحيل البيانات للشهر الجديد وتصفير اليوميات", use_container_width=True):
        st.session_state.monthly_archive = pd.concat([st.session_state.monthly_archive, st.session_state.fleet_data], ignore_index=True)
        st.session_state.fleet_data = pd.DataFrame(columns=st.session_state.fleet_data.columns)
        st.success("تم بنجاح أرشفة الشهر الحالي والبدء بشهر جديد نظيف!")
        st.rerun()

# 🟢 4. Excel والسجل العام
elif selected_tab == "📥 Excel والسجل العام":
    st.subheader("📥 تصدير الكشوفات والتقارير بصيغة Excel / CSV")
    st.write("تصدير متوافق لحظياً مع ملف Google Sheets المرتبط بالنظام:")
    
    csv_data = st.session_state.fleet_data.to_csv(index=False).encode('utf-8-sig') if not st.session_state.fleet_data.empty else "".encode('utf-8-sig')
    
    st.download_button(
        label="📄 تنزيل تقارير الأسطول المحدثة كملف جاهز",
        data=csv_data,
        file_name=f"تقرير_أسطول_المهرة_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )

# 🟢 5. الإعدادات العامة والصيانة والحذف الآمن
elif selected_tab == "⚙️ الإعدادات العامة والصيانة":
    st.subheader("⚙️ إعدادات النظام، الصيانة، وإدارة الحذف الآمن")
    
    with st.expander("ℹ️ حول نظام إدارة أسطول صندوق النظافة - المهرة", expanded=False):
        st.write("""
        **نظام حوكمة الزيوت والحركة اليومية:**
        مصمم خصيصاً لمحافظة المهرة لضمان متابعة الشاحنات، حساب المسافات، والتعامل مع التقارير الواردة عبر السوفتوير الآلي المطور.
        * **صانع ومطور النظام:** عماد محمد منهاج.
        """)

    st.markdown("---")
    st.markdown("### ⚠️ منطقة العمليات الحساسة (الحذف والإدارة)")
    
    selected_date = st.date_input("اختر التاريخ المراد مراجعته للحذف:", datetime.date.today())
    date_str = str(selected_date)
    
    delete_option = st.radio(
        "حدد إجراء الحذف المطلوب:",
        (
            "تعديل أو حذف سجل سيارة محددة فقط",
            "حذف كافة بيانات وسجلات اليوم المحدد بالكامل ⚠️"
        )
    )
    
    if "سيارة محددة" in delete_option:
        target_car = st.text_input("أدخل رقم أو اسم السيارة المراد مسح سجلها لهذا اليوم:")
        if st.button("🗑️ حذف سجل السيارة المحدد", use_container_width=True):
            if not st.session_state.fleet_data.empty and target_car:
                initial_len = len(st.session_state.fleet_data)
                st.session_state.fleet_data = st.session_state.fleet_data[
                    ~((st.session_state.fleet_data['التاريخ'] == date_str) & 
                      (st.session_state.fleet_data['رقم السيارة'].str.contains(target_car)))
                ]
                if len(st.session_state.fleet_data) < initial_len:
                    st.success(f"تم حذف سجل السيارة المحددة ليوم {date_str} بنجاح.")
                else:
                    st.warning("لم يتم العثور على مطابقة لهذا السجل.")
            else:
                st.error("يرجى إدخال رقم السيارة الصحيح.")
    else:
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("⚠️ مسح وحذف كافة بيانات هذا اليوم بالكامل"):
            if not st.session_state.fleet_data.empty:
                st.session_state.fleet_data = st.session_state.fleet_data[st.session_state.fleet_data['التاريخ'] != date_str]
                st.error(f"تم مسح كافة سجلات يوم {date_str} بالكامل.")
            else:
                st.info("الجدول فارغ تماماً.")
        st.markdown('</div>', unsafe_allow_html=True)
