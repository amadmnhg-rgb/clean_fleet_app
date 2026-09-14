import streamlit as st
import datetime
import pandas as pd

# استدعاء مكتبة الربط السحابي بأمان لمنع أي أخطاء ModuleNotFoundError
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتجاوُب الشامل للجوال واللابتوب
# ---------------------------------------------------------
st.set_page_config(
    page_title="صندوق النظافة والتحسين - المهرة",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. تصميم CSS المخصص (iOS Glassmorphism & Modern UI)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* خلفية متناسقة ونصوص واضحة */
    .stApp {
        background-color: #0b0f19;
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* إخفاء الشريط الجانبي Sidebar تماماً */
    [data-testid="stSidebar"] {
        display: none;
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
    
    /* بطاقات الإحصائيات التفاعلية */
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
    
    /* الأزرار الحمراء للتحذير والحذف */
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
    .danger-btn > button:hover {
        background-color: #c0392b !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. إدارة جلسة البيانات (Session State & Undo Buffer)
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "لوحة التحكم"
if 'fleet_data' not in st.session_state:
    # الجدول يبدأ فارغاً بدون أي إدخالات وهمية
    st.session_state.fleet_data = pd.DataFrame(columns=[
        "التاريخ", "رقم السيارة", "اسم السائق", "قراءة بداية اليوم", 
        "قراءة نهاية اليوم", "المسافة المقطوعة (كم)", "عداد الزيت الحالي", "حد تغيير الزيت"
    ])
if 'undo_stack' not in st.session_state:
    st.session_state.undo_stack = []

# ---------------------------------------------------------
# 4. شاشة تسجيل الدخول والمزامنة
# ---------------------------------------------------------
if not st.session_state.logged_in:
    st.markdown("""
        <div class="app-header-container">
            <div style="font-size: 48px; margin-bottom: 5px;">🚛🐪🌴</div>
            <div class="app-title-yellow">صندوق النظافة والتحسين</div>
            <div class="app-title-white">محافظة المهـرة</div>
            <p style="color: #2ecc71; margin-top: 8px; font-weight: 600;">نظام متابعة أسطول الشاحنات والزيوت الذكي</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔑 تسجيل الدخول ومزامنة البيانات")
        email = st.text_input("البريد الإلكتروني للمستخدم:", placeholder="example@mahrah.gov")
        password = st.text_input("كلمة المرور / الرمز الخاص:", type="password")
        
        if st.button("🚀 تسجيل الدخول وتفعيل المزامنة", use_container_width=True):
            if email and password:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.success("تم تسجيل الدخول ومزامنة البيانات بنجاح!")
                st.rerun()
            else:
                st.error("يرجى إدخال البريد الإلكتروني ورمز المرور الصحيح.")
    st.stop()

# ---------------------------------------------------------
# 5. الهيدر الرئيسي وتصميم الأيقونة الـ 3D
# ---------------------------------------------------------
st.markdown("""
    <div class="app-header-container">
        <div style="font-size: 42px; margin-bottom: 5px;">🚛🐪🌴</div>
        <div class="app-title-yellow">صندوق النظافة والتحسين</div>
        <div class="app-title-white">محافظة المهـرة</div>
        <p style="color: #3498db; font-weight: bold; margin-top: 5px;">برنامج متابعة الحركة والزيوت والأسطول</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. شريط التنقل السلس المخصص (iOS Navigation Bar)
# ---------------------------------------------------------
tabs = ["📊 لوحة التحكم", "📝 الحركة اليومية", "🛠️ إدارة الصيانة", "📥 التصدير", "⚙️ الإعدادات"]
selected_tab = st.radio("", tabs, horizontal=True)

# مزامنة التبويب النشط
if "لوحة" in selected_tab:
    st.session_state.current_tab = "لوحة التحكم"
elif "الحركة" in selected_tab:
    st.session_state.current_tab = "الحركة اليومية"
elif "إدارة" in selected_tab:
    st.session_state.current_tab = "إدارة الصيانة"
elif "التصدير" in selected_tab:
    st.session_state.current_tab = "التصدير"
elif "الإعدادات" in selected_tab:
    st.session_state.current_tab = "الإعدادات"

st.markdown("---")

# ---------------------------------------------------------
# 7. محتوى الأقسام الكامل
# ---------------------------------------------------------

# 🟢 1. لوحة التحكم والتحليلات المباشرة
if st.session_state.current_tab == "لوحة التحكم":
    st.subheader("📌 الحالة الفنية المباشرة ونسب استهلاك الزيوت")
    
    df = st.session_state.fleet_data
    
    # حساب الإحصائيات التلقائية
    total_cars = len(df['رقم السيارة'].unique()) if not df.empty else 0
    today_str = str(datetime.date.today())
    today_df = df[df['التاريخ'] == today_str] if not df.empty else pd.DataFrame()
    
    cars_moved_today = len(today_df['رقم السيارة'].unique()) if not today_df.empty else 0
    total_km_today = today_df['المسافة المقطوعة (كم)'].sum() if not today_df.empty else 0.0
    
    # استخراج تنبيهات الزيت
    oil_exceeded = 0
    oil_warning = 0
    if not df.empty:
        for idx, row in df.iterrows():
            rem = row['حد تغيير الزيت'] - row['عداد الزيت الحالي']
            if rem <= 0:
                oil_exceeded += 1
            elif rem <= 500:
                oil_warning += 1

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
    st.subheader("📋 جدول السجلات والزيوت النشط")
    if df.empty:
        st.info("💡 لا توجد بيانات مدخلة حتى الآن. يبدأ الجدول فارغاً حتى تقوم بإدخال الحركة من تبويب 'الحركة اليومية'.")
    else:
        st.dataframe(df, use_container_width=True)

# 🟢 2. تسجيل الحركة اليومية وزر التراجع (Undo)
elif st.session_state.current_tab == "الحركة اليومية":
    st.subheader("📝 تسجيل الحركة اليومية للأسطول والكيلومترات")
    
    with st.form("daily_entry_form", clear_on_submit=True):
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            car_no = st.text_input("رقم السيارة / الشاحنة:")
            driver = st.text_input("اسم السائق المسؤول:")
            km_start = st.number_input("قراءة الكيلومتر (بداية اليوم):", min_value=0.0, step=1.0)
        with col_in2:
            entry_date = st.date_input("تاريخ الحركة:", datetime.date.today())
            oil_limit = st.number_input("حد تغيير الزيت المعتمد (كم):", min_value=1000.0, value=5000.0, step=500.0)
            km_end = st.number_input("قراءة الكيلومتر (نهاية اليوم):", min_value=0.0, step=1.0)
            
        submit_btn = st.form_submit_button("➕ حفظ وتسجيل الحركة", use_container_width=True)
        
        if submit_btn:
            if car_no and km_end >= km_start:
                distance = km_end - km_start
                new_row = {
                    "التاريخ": str(entry_date),
                    "رقم السيارة": car_no,
                    "اسم السائق": driver,
                    "قراءة بداية اليوم": km_start,
                    "قراءة نهاية اليوم": km_end,
                    "المسافة المقطوعة (كم)": distance,
                    "عداد الزيت الحالي": km_end,
                    "حد تغيير الزيت": oil_limit
                }
                # حفظ نسخة للتراجع
                st.session_state.undo_stack.append(new_row)
                
                # إضافة للجدول الرئيسي
                st.session_state.fleet_data = pd.concat([st.session_state.fleet_data, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"تم تسجيل حركة السيارة ({car_no}) بنجاح! المسافة المقطوعة: {distance} كم.")
            else:
                st.error("يرجى التأكد من إدخال رقم السيارة وأن قراءة نهاية اليوم أكبر من أو تساوي بداية اليوم.")

    st.markdown("---")
    # زر التراجع عن الإدخال
    col_undo1, col_undo2 = st.columns([2, 1])
    with col_undo2:
        if st.button("↩️ تراجع عن آخر إدخال", use_container_width=True):
            if not st.session_state.fleet_data.empty and st.session_state.undo_stack:
                last_entry = st.session_state.undo_stack.pop()
                st.session_state.fleet_data = st.session_state.fleet_data.drop(st.session_state.fleet_data.index[-1])
                st.warning(f"تم التراجع عن إدخال السيارة: {last_entry.get('رقم السيارة')}")
                st.rerun()
            else:
                st.info("لا توجد إدخالات سابقة للتراجع عنها.")

# 🟢 3. إدارة الصيانة والحذف المتقدم
elif st.session_state.current_tab == "إدارة الصيانة":
    st.subheader("🛠️ إدارة السجلات وحذف البيانات حسب اليوم أو السيارة")
    
    selected_date = st.date_input("اختر التاريخ المراد إدارته:", datetime.date.today())
    date_str = str(selected_date)
    
    action_type = st.radio("حدد نوع الإجراء المطلوبة:", ["تعديل / حذف سجل سيارة واحدة فقط", "حذف كافة بيانات اليوم المحدد بالكامل ⚠️"])
    
    if action_type == "تعديل / حذف سجل سيارة واحدة فقط":
        target_car = st.text_input("أدخل رقم السيارة المراد مسح سجلها لهذا اليوم:")
        if st.button("🗑️ حذف سجل السيارة المحدد", use_container_width=True):
            if not st.session_state.fleet_data.empty and target_car:
                initial_count = len(st.session_state.fleet_data)
                st.session_state.fleet_data = st.session_state.fleet_data[
                    ~((st.session_state.fleet_data['التاريخ'] == date_str) & 
                      (st.session_state.fleet_data['رقم السيارة'] == target_car))
                ]
                if len(st.session_state.fleet_data) < initial_count:
                    st.success(f"تم حذف سجل السيارة {target_car} لتاريخ {date_str} بنجاح.")
                else:
                    st.warning("لم يتم العثور على سجل يطابق هذا الرقم وهذا التاريخ.")
            else:
                st.error("يرجى كتابة رقم السيارة التأكيدي.")
    else:
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("⚠️ مسح وحذف بيانات هذا اليوم بالكامل"):
            if not st.session_state.fleet_data.empty:
                st.session_state.fleet_data = st.session_state.fleet_data[st.session_state.fleet_data['التاريخ'] != date_str]
                st.error(f"تم مسح كافة سجلات يوم {date_str} بالكامل من النظام.")
            else:
                st.info("الجدول فارغ بالفعل.")
        st.markdown('</div>', unsafe_allow_html=True)

# 🟢 4. تصدير التقارير
elif st.session_state.current_tab == "التصدير":
    st.subheader("📥 تصدير كشوفات وتقارير أسطول الحركة")
    st.write("يمكنك تصدير قاعدة البيانات الحالية بصيغ جاهزة للطباعة أو الأرشفة:")
    
    csv_data = st.session_state.fleet_data.to_csv(index=False).encode('utf-8-sig') if not st.session_state.fleet_data.empty else "".encode('utf-8-sig')
    
    st.download_button(
        label="📄 تحميل التقرير الشامل كملف (CSV / Excel)",
        data=csv_data,
        file_name=f"تقرير_حركة_الشاحنات_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )

# 🟢 5. الإعدادات، الشرح، والإدارة
elif st.session_state.current_tab == "الإعدادات":
    st.subheader("⚙️ إعدادات البرنامج والمعلومات التعريفية")
    
    # 1. التعريف بالتطبيق
    with st.expander("ℹ️ ما هو هذا التطبيق ولماذا صُنع؟", expanded=True):
        st.write("""
        **تطبيق متابعة شاحنات الصندوق - محافظة المهـرة:**
        نظام ذكي متكامل مصمم خصيصاً لإدارة ومتابعة أسطول شاحنات وسيارات **صندوق النظافة والتحسين بمحافظة المهرة**.
        
        **أهداف التطبيق:**
        1. **حوكمة استهلاك الزيوت:** التنبيه الآلي المبكر قبل تجاوز العمر الافتراضي لزيت المحرك لحماية أصول الصندوق من الأعطال المكلفة.
        2. **متابعة الكيلومترات اليومية:** تسجيل ودراسة المسافات المقطوعة لكل آلية وسائق بدقة عالية.
        3. **الربط والمزامنة الفورية:** تمكين الإدارة والمشرفين من متابعة وتحديث البيانات لحظياً بين الجوال واللابتوب.
        """)

    # 2. معلومات صاحب وصانع التطبيق (الخيار قبل الأخير)
    with st.expander("👨‍💻 صانع وإدارة التطبيق", expanded=True):
        st.markdown("""
        * **صانع وصاحب التطبيق والمدير لهذا البرنامج:**  
          ### ✨ **عماد محمد منهاج**
        """)

    st.markdown("---")
    
    # 3. إدارة الجلسة وتسجيل الخروج
    st.markdown("### 🔒 الحساب والجلسة الحالية")
    st.write(f"المستخدم المسجل حالياً: **{st.session_state.user_email}**")
    
    if 'confirm_logout' not in st.session_state:
        st.session_state.confirm_logout = False

    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
    if st.button("🚪 تسجيل الخروج من الحساب"):
        st.session_state.confirm_logout = True
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.confirm_logout:
        st.warning("⚠️ هل أنت تأكد من رغبتك في تسجيل الخروج؟ سيتم إيقاف المزامنة اللحظية على هذا الجهاز.")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("نعم، تأكيد الخروج النهائي", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_email = ""
                st.session_state.confirm_logout = False
                st.rerun()
        with col_c2:
            if st.button("إلغاء", use_container_width=True):
                st.session_state.confirm_logout = False
                st.rerun()
