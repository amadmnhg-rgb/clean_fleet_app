import streamlit as st
import datetime
import pandas as pd
import re

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
# 2. تصميم CSS المطور المتوافق تلقائياً مع الثيم (Light / Dark)
# ---------------------------------------------------------
st.markdown("""
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

<style>
    /* تطبيق الخط العصري على كافة عناصر التطبيق */
    .stApp, html, body, [class*="css"] {{
        font-family: 'Cairo', sans-serif !important;
    }}

    /* استجابة تلقائية كاملة لثيم ستريملت (النهاري والداكن) */
    .stApp {{
        background-color: var(--background-color);
        color: var(--text-color);
    }}
    
    /* شريط جانبي متناسق مع الثيم المختار */
    [data-testid="stSidebar"] {{
        background-color: var(--secondary-background-color);
        border-left: 1px solid rgba(128, 128, 128, 0.15);
    }}
    
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {{
        color: var(--text-color) !important;
        font-weight: 600 !important;
    }}
    
    /* الهيدر الرئيسي بأسلوب Glassmorphism 3D متكيف */
    .app-header-container {{
        background: var(--secondary-background-color);
        border: 1px solid rgba(46, 204, 113, 0.35);
        border-radius: 22px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
        margin-bottom: 25px;
    }}
    
    .app-title-yellow {{
        color: #27ae60;
        font-size: 27px;
        font-weight: 900;
        margin-bottom: -3px;
    }}
    
    .app-title-white {{
        color: var(--text-color);
        font-size: 22px;
        font-weight: 800;
    }}
    
    /* بطاقات الإحصائيات المتكيفة مع وضع الإضاءة */
    .stat-card {{
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 18px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
    }}
    .stat-card:hover {{
        border-color: rgba(46, 204, 113, 0.5);
        transform: translateY(-3px);
    }}
    
    /* تنسيق الجداول لتتلائم تلقائياً مع الثيم */
    [data-testid="stDataFrame"] {{
        background: var(--secondary-background-color);
        border-radius: 14px;
        border: 1px solid rgba(128, 128, 128, 0.15);
        padding: 5px;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. إدارة جلسة البيانات وتسجيل الدخول الدائم والآمن
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = True

if 'fleet_data' not in st.session_state:
    st.session_state.fleet_data = pd.DataFrame(columns=[
        "التاريخ", "رقم السيارة", "عدد الزفات", "تفاصيل الزفات", 
        "المسافة المقطوعة (كم)", "الوقت المستغرق", "عداد الزيت الحالي", "حد تغيير الزيت"
    ])

if 'undo_stack' not in st.session_state:
    st.session_state.undo_stack = []

if not st.session_state.logged_in:
    st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <h2>🔒 تم تسجيل خروجك بنجاح من النظام</h2>
            <p>يرجى إعادة تحديث الصفحة أو تسجيل الدخول من جديد.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🔄 تسجيل الدخول مرة أخرى"):
        st.session_state.logged_in = True
        st.rerun()
    st.stop()

# ---------------------------------------------------------
# 4. محرك استخلاص وترتيب رسائل الحركة اليومية أوتوماتيكياً
# ---------------------------------------------------------
def parse_daily_fleet_messages(raw_text):
    entries = []
    blocks = re.split(r'(?=سيارة\s*رقم|شاحنة\s*رقم)', raw_text)
    
    for block in blocks:
        if not block.strip():
            continue
            
        car_match = re.search(r'(?:سيارة|شاحنة)\s*رقم\s*(\d+)', block)
        car_no = f"سيارة رقم {car_match.group(1)}" if car_match else "غير محدد"
        
        dist_match = re.search(r'المسافه[:\s]*([\d\.]+)\s*كم', block)
        distance = float(dist_match.group(1)) if dist_match else 0.0
        
        time_match = re.search(r'الوقت[:\s]*([^\n]+)', block)
        time_spent = time_match.group(1).strip() if time_match else "غير محدد"
        
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
            "عداد الزيت الحالي": distance * 2,
            "حد تغيير الزيت": 5000.0
        })
    return entries

# ---------------------------------------------------------
# 5. الشريط الجانبي للتنقل
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🚛 قائمة التحكم الذكية")
    selected_tab = st.radio(
        "الانتقال إلى:",
        (
            "📊 لوحة التحكم الرئيسية",
            "📝 الحركة اليومية (قراءة الرسائل)",
            "📋 السجل الشهري المجدول",
            "📁 السجل العام (Excel)",
            "⚙️ الإعدادات العامة والصيانة"
        ),
        label_visibility="collapsed"
    )

# ---------------------------------------------------------
# 6. الهيدر الرئيسي للتطبيق
# ---------------------------------------------------------
st.markdown("""
    <div class="app-header-container">
        <div style="font-size: 38px; margin-bottom: 5px;">🚛🐪🌴</div>
        <div class="app-title-yellow">صندوق النظافة والتحسين</div>
        <div class="app-title-white">محافظة المهـرة</div>
        <p style="color: #3498db; font-weight: bold; margin-top: 5px; font-size: 14px;">نظام إدارة الأسطول والزيوت الذكي - متزامن لحظياً</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. محتوى الأقسام التفاعلية
# ---------------------------------------------------------

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
        st.markdown(f'<div class="stat-card"><h3 style="color:#e74c3c; margin:0;">{oil_exceeded}</h3><p style="margin:5px 0 0 0; font-size:13px;">تجاوزت حد الزيت ⚠️</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h3 style="color:#f39c12; margin:0;">{oil_warning}</h3><p style="margin:5px 0 0 0; font-size:13px;">تحتاج صيانة قريباً 🛠️</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h3 style="color:#3498db; margin:0;">{total_km_today:.1f}</h3><p style="margin:5px 0 0 0; font-size:13px;">مسافة اليوم (كم) 🛣️</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h3 style="color:#2ecc71; margin:0;">{cars_moved_today}</h3><p style="margin:5px 0 0 0; font-size:13px;">تحركت اليوم 🚛</p></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="stat-card"><h3 style="color:#9b59b6; margin:0;">{total_cars}</h3><p style="margin:5px 0 0 0; font-size:13px;">إجمالي السيارات 🚚</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📋 جدول السجلات الحية لليوم (مباشر ومحدث)")
    
    if today_df.empty:
        st.info("💡 لا توجد بيانات مسجلة اليوم حتى الآن. قم بلصق تقارير ورسائل السائقين في قسم 'الحركة اليومية (قراءة الرسائل)' لتظهر هنا فوراً.")
    else:
        st.dataframe(today_df, use_container_width=True)

elif selected_tab == "📝 الحركة اليومية (قراءة الرسائل)":
    st.subheader("📥 قراءة واستخلاص تقارير الحركة والرسائل اليومية دفعة واحدة")
    st.write("قم بلصق تقارير السائقين هنا، وسيقوم النظام بفرزها وترتيبها لتظهر مباشرة في السجلات الحية:")
    
    with st.form("bulk_message_form"):
        raw_messages = st.text_area(
            "صندوق إدخال الرسائل اليومية:",
            placeholder="سيارة رقم 1\nثلاث زفات من المحرقة\nزفه الصباح الساعة 9:39\nالمسافه 66 كم...",
            height=200
        )
        process_btn = st.form_submit_button("🚀 تحليل واستخلاص وتسجيل البيانات أوتوماتيكياً", use_container_width=True)
        
        if process_btn and raw_messages.strip():
            extracted_items = parse_daily_fleet_messages(raw_messages)
            if extracted_items:
                new_df = pd.DataFrame(extracted_items)
                st.session_state.undo_stack.append(new_df)
                st.session_state.fleet_data = pd.concat([st.session_state.fleet_data, new_df], ignore_index=True)
                st.success(f"تم بنجاح استخلاص وتسجيل بيانات {len(extracted_items)} شاحنات وتحديث السجلات الحية لليوم!")
                st.rerun()
            else:
                st.warning("تعذر استخراج البيانات. تأكد من تطابق نمط النص مع التقارير المطلوبة.")

    st.markdown("---")
    if st.button("↩️ تراجع عن آخر إدخال مجمع", use_container_width=True):
        if st.session_state.undo_stack:
            last_batch = st.session_state.undo_stack.pop()
            st.session_state.fleet_data = st.session_state.fleet_data.iloc[:-len(last_batch)]
            st.warning("تم التراجع وحذف آخر دفعة تم إدخالها بنجاح.")
            st.rerun()
        else:
            st.info("لا توجد إدخالات سابقة للتراجع عنها.")

elif selected_tab == "📋 السجل الشهري المجدول":
    st.subheader("📅 أرشيف السجلات الشهرية وحالة الأسطول المجمعة")
    if not st.session_state.fleet_data.empty:
        monthly_summary = st.session_state.fleet_data.groupby("رقم السيارة").agg({
            "المسافة المقطوعة (كم)": "sum",
            "عدد الزفات": "sum"
        }).reset_index()
        monthly_summary["الشهر الحالي"] = str(datetime.date.today().strftime("%Y-%m"))
        st.dataframe(monthly_summary, use_container_width=True)
    else:
        st.info("السجل الشهري سيتم تعبئته تلقائياً مع تراكم الحركات اليومية.")

elif selected_tab == "📁 السجل العام (Excel)":
    st.subheader("📥 تصدير الكشوفات والتقارير بصيغة Excel / CSV")
    st.write("ملف متوافق لحظياً مع جداول الأسطول والربط السحابي:")
    
    csv_data = st.session_state.fleet_data.to_csv(index=False).encode('utf-8-sig') if not st.session_state.fleet_data.empty else "".encode('utf-8-sig')
    st.download_button(
        label="📄 تنزيل تقارير الأسطول المحدثة كملف جاهز",
        data=csv_data,
        file_name=f"تقرير_أسطول_المهرة_{datetime.date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )

elif selected_tab == "⚙️ الإعدادات العامة والصيانة":
    st.subheader("⚙️ إعدادات النظام، المظهر، وصيانة الأسطول")
    
    with st.expander("🎨 إرشادات تغيير الثيم المظهر", expanded=True):
        st.info("💡 **ملاحظة:** يمكنك تغيير الثيم فوراً (إلى النهاري أو الداكن) بالضغط على زر **الإعدادات (Settings)** من القائمة العلوية الثلاث نقاط في الزاوية، وسيتكيف التطبيق بالكامل تلقائياً معه فوراً دون الحاجة لإعدادات إضافية!")

    with st.expander("ℹ️ حول نظام إدارة أسطول صندوق النظافة - المهرة", expanded=False):
        st.write("نظام حوكمة الزيوت والحركة اليومية - مطور خصيصاً لمحافظة المهرة. صانع النظام: عماد محمد منهاج.")
    
    st.markdown("---")
    st.markdown("### 🚪 إدارة الحساب وجلسة الدخول")
    if st.button("🔒 تسجيل الخروج من الحساب الحالي", type="secondary", use_container_width=True):
        st.session_state.logged_in = False
        st.success("تم تسجيل الخروج بنجاح.")
        st.rerun()

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
        if st.button("⚠️ مسح وحذف كافة بيانات هذا اليوم بالكامل", type="primary"):
            if not st.session_state.fleet_data.empty:
                st.session_state.fleet_data = st.session_state.fleet_data[st.session_state.fleet_data['التاريخ'] != date_str]
                st.error(f"تم مسح كافة سجلات يوم {date_str} بالكامل.")
            else:
                st.info("الجدول فارغ تماماً.")
