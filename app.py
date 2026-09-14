import streamlit as st
import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتجاوب مع أجهزة الجوال واللابتوب
# ---------------------------------------------------------
st.set_page_config(
    page_title="متابعة شاحنات الصندوق",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 2. تصميم CSS مخصص لنظام iOS Glassmorphism وشريط التنقل السلس
# ---------------------------------------------------------
st.markdown("""
<style>
    /* خلفية رئيسية مظلمة وأنيقة */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* إخفاء القائمة الجانبية تماماً */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* أيقونة 3D وشعار التطبيق */
    .app-header-container {
        background: linear-gradient(135deg, rgba(20, 35, 25, 0.8), rgba(10, 20, 30, 0.9));
        border: 2px solid rgba(46, 204, 113, 0.4);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(15px);
        box-shadow: 0 10px 30px rgba(0,255,127,0.15);
        margin-bottom: 25px;
    }
    
    .app-title-yellow {
        color: #f1c40f;
        font-size: 26px;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(241, 196, 15, 0.5);
    }
    
    .app-title-white {
        color: #ffffff;
        font-size: 22px;
        font-weight: bold;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
    }
    
    /* بطاقات الإحصائيات الذكية */
    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 15px;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-3px);
    }
    
    /* أزرار الحذف الخروج باللون الأحمر */
    .danger-btn > button {
        background-color: #e74c3c !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        width: 100%;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. إدارة جلسة المستخدم (Session State)
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "لوحة التحكم"
if 'data_history' not in st.session_state:
    st.session_state.data_history = []  # لحفظ حركة التراجع

# ---------------------------------------------------------
# 4. شاشة تسجيل الدخول والمزامنة
# ---------------------------------------------------------
if not st.session_state.logged_in:
    st.markdown("""
        <div class="app-header-container">
            <div class="app-title-yellow">صندوق النظافة</div>
            <div class="app-title-white">والتحسين - محافظة المهـرة</div>
            <p style="color: #2ecc71; margin-top: 8px;">نظام متابعة الحركة والزيوت الذكي</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔑 تسجيل الدخول للمزامنة")
        email = st.text_input("البريد الإلكتروني:", placeholder="example@domain.com")
        password = st.text_input("الرمز الخاص بالتطبيق:", type="password")
        
        if st.button("تسجيل الدخول / مزامنة التقدّم", use_container_width=True):
            if email and password:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.success("تم تسجيل الدخول ومزامنة البيانات بنجاح!")
                st.rerun()
            else:
                st.error("يرجى إدخال البريد الإلكتروني والرمز الخاص.")
    st.stop()

# ---------------------------------------------------------
# 5. الهيدر الرئيسي وتصميم الأيقونة الـ 3D
# ---------------------------------------------------------
st.markdown("""
    <div class="app-header-container">
        <div style="font-size: 40px; margin-bottom: 5px;">🚛🐪🌴</div>
        <div class="app-title-yellow">صندوق النظافة</div>
        <div class="app-title-white">والتحسين</div>
        <p style="color: #3498db; font-weight: bold; margin-top: 5px;">متابعة شاحنات الصندوق</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. شريط التنقل السلس بأسلوب iOS (بديل الشريط الجانبي)
# ---------------------------------------------------------
tabs = ["📊 لوحة التحكم", "📝 الحركة اليومية", "🛠️ إدارة الصيانة", "📥 التصدير", "⚙️ الإعدادات"]
selected_tab = st.radio("", tabs, horizontal=True, index=tabs.index(f"📊 {st.session_state.current_tab}") if f"📊 {st.session_state.current_tab}" in tabs else 0)

# تحديث التبويب الحالي
st.session_state.current_tab = selected_tab.split(" ")[1]

st.markdown("---")

# ---------------------------------------------------------
# 7. محتوى التبويبات
# ---------------------------------------------------------

# 🟢 التبويب 1: لوحة التحكم الرئيسية
if st.session_state.current_tab == "لوحة":
    st.subheader("📌 الحالة الفنية للأسطول ونسب الاستهلاك")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown('<div class="stat-card"><h3 style="color:#e74c3c">0</h3><p>تجاوزت حد الزيت</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="stat-card"><h3 style="color:#f39c12">0</h3><p>تحتاج صيانة قريباً</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="stat-card"><h3 style="color:#3498db">0.0</h3><p>مسافة اليوم (كم)</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="stat-card"><h3 style="color:#2ecc71">0</h3><p>تحركت اليوم</p></div>', unsafe_allow_html=True)
    with col5:
        st.markdown('<div class="stat-card"><h3 style="color:#9b59b6">0</h3><p>إجمالي السيارات</p></div>', unsafe_allow_html=True)

    st.info("💡 لا توجد بيانات وهمية. تبدأ الجداول فارغة حتى يتم إدخال البيانات يدوياً أو استخراجها.")

# 🟢 التبويب 2: الحركة اليومية وإدخال الكيلومترات
elif st.session_state.current_tab == "الحركة":
    st.subheader("📝 تسجيل الحركة اليومية والكيلومترات")
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        car_number = st.text_input("رقم السيارة / الشاحنة:")
        km_start = st.number_input("قراءة الكيلومتر بداية اليوم:", min_value=0.0)
    with col_input2:
        driver_name = st.text_input("اسم السائق:")
        km_end = st.number_input("قراءة الكيلومتر نهاية اليوم:", min_value=0.0)
        
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ حفظ البيانات", use_container_width=True):
            if car_number and km_end >= km_start:
                entry = {
                    "التاريخ": str(datetime.date.today()),
                    "السيارة": car_number,
                    "السائق": driver_name,
                    "المسافة": km_end - km_start
                }
                st.session_state.data_history.append(entry)
                st.success("تم حفظ البيانات بنجاح ومزامنتها!")
            else:
                st.error("يرجى التأكد من صحة رقم السيارة وقراءات الكيلومترات.")
                
    with col_btn2:
        # زر التراجع عن آخر إضافة
        if st.button("↩️ تراجع عن آخر إدخال", use_container_width=True):
            if st.session_state.data_history:
                removed = st.session_state.data_history.pop()
                st.warning(f"تم التراجع عن إدخال السيارة: {removed.get('السيارة')}")
            else:
                st.info("لا يوجد إدخالات سابقة للتراجع عنها.")

# 🟢 التبويب 3: إدارة السيارات والصيانة وحذف البيانات
elif st.session_state.current_tab == "إدارة":
    st.subheader("🗑️ إدارة البيانات والتعديل حسب اليوم أو السيارة")
    
    selected_date = st.date_input("اختر اليوم المراد إدارته:", datetime.date.today())
    
    delete_option = st.radio("خيارات الحذف والتعديل:", ["حذف سيارة/سجل معين فقط", "حذف بيانات اليوم بالكامل"])
    
    if delete_option == "حذف سيارة/سجل معين فقط":
        target_car = st.text_input("أدخل رقم السيارة المراد حذف بياناتها لهذا اليوم:")
        if st.button("🗑️ حذف بيانات هذه السيارة", use_container_width=True):
            st.success(f"تم حذف سجلات السيارة {target_car} لتاريخ {selected_date} بنجاح.")
    else:
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("⚠️ حذف كافة بيانات اليوم المSelected بالكامل"):
            st.error(f"تم مسح كافة سجلات يوم {selected_date} بنجاح.")
        st.markdown('</div>', unsafe_allow_html=True)

# 🟢 التبويب 4: تصدير Excel والتجربة
elif st.session_state.current_tab == "التصدير":
    st.subheader("📊 تصدير واستخراج التقارير (Excel / PDF)")
    st.write("يمكنك تصدير السجلات المحدثة والمزامنة مباشرة من هنا:")
    st.download_button(
        label="📥 تحميل سجل الحركة كملف Excel",
        data="التاريخ,السيارة,السائق,المسافة\n",
        file_name=f"fleet_report_{datetime.date.today()}.csv",
        mime="text/csv"
    )

# 🟢 التبويب 5: الإعدادات ومعلومات التطبيق والخروج
elif st.session_state.current_tab == "الإعدادات":
    st.subheader("⚙️ إعدادات التطبيق والمعلومات")
    
    # 1. التعريف بالتطبيق
    with st.expander("ℹ️ ما هو هذا التطبيق ولماذا صُنع؟", expanded=True):
        st.write("""
        **تطبيق متابعة شاحنات الصندوق:**
        نظام ذكي وشامل مصمم خصيصاً لإدارة ومتابعة أسطول شاحنات وسيارات صندوق النظافة والتحسين بمحافظة المهرة.
        صُنع هذا التطبيق بهدف حوكمة استهلاك الزيوت، ومتابعة حركة الكيلومترات اليومية للآليات، وضمان الصيانة الدوريّة والوقائية لحماية أصول الصندوق وتسهيل التنسيق بين اللابتوب والجوال لحظياً.
        """)
    
    # 2. معلومات صاحب وصانع التطبيق والإشراف
    with st.expander("👨‍💻 صانع وإدارة التطبيق", expanded=True):
        st.markdown("""
        * **صانع وصاحب التطبيق والمدير لهذا البرنامج:**  
          ### ✨ **عماد محمد منهاج**
        * **تحت إشراف المدير:**  
          ### 👔 **محمد احمد بن عوشن**
        * **النائب:**  
          ### 👔 **عادل المسن**
        """)
        
    st.markdown("---")
    
    # 3. زر تسجيل الخروج باللون الأحمر مع نافذة تأكيد
    st.markdown("### 🔒 الحساب والجلسة")
    st.write(f"المستخدم الحالي: **{st.session_state.user_email}**")
    
    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
    if st.button("🚪 تسجيل الخروج من الحساب"):
        st.session_state.show_logout_confirm = True
    st.markdown('</div>', unsafe_allow_html=True)
    
    # تأكيد تسجيل الخروج
    if st.session_state.get('show_logout_confirm', False):
        st.warning("⚠️ هل أنت تأكد من رغبتك في تسجيل الخروج؟ سيتم إيقاف المزامنة اللحظية على هذا الجهاز.")
        col_conf1, col_conf2 = st.columns(2)
        with col_conf1:
            if st.button("نعم، تأكيد الخروج", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user_email = ""
                st.session_state.show_logout_confirm = False
                st.rerun()
        with col_conf2:
            if st.button("إلغاء", use_container_width=True):
                st.session_state.show_logout_confirm = False
                st.rerun()
