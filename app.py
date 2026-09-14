import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io

# 1. تهيئة وتكوين الصفحة
st.set_page_config(
    page_title="صندوق النظافة والتحسين - م/ المهرة", 
    page_icon="🚛", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. حقن ستايل CSS زجاجي ومتطور (Glassmorphism & Squircle UI)
glass_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif !important;
    }

    /* خلفية زجاجية متدرجة للتطبيق */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        color: #f8fafc;
    }

    /* رأس الصفحة (Header Bar الزجاجي) */
    .header-glass {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 24px;
        padding: 20px 30px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .header-title-container {
        display: flex;
        align-items: center;
        gap: 20px;
    }

    .logo-img {
        width: 85px;
        height: 85px;
        border-radius: 50%;
        border: 2px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
        object-fit: cover;
    }

    /* بطاقات Squircle الزجاجية */
    .squircle-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 22px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease-in-out;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        margin-bottom: 15px;
    }

    .squircle-card:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.25);
    }

    .card-icon {
        font-size: 2.2rem;
        margin-bottom: 8px;
    }

    .card-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #ffffff;
    }

    .card-label {
        font-size: 0.95rem;
        color: #94a3b8;
        font-weight: 500;
    }

    /* القائمة الجانبية الزجاجية */
    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.75) !important;
        backdrop-filter: blur(20px);
        border-left: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* إخفاء العلامة المائية للرابط العلوي */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* أشرطة التقدم المخصصة */
    .stProgress > div > div > div > div {
        border-radius: 10px;
    }
</style>
"""
st.markdown(glass_css, unsafe_allow_html=True)

# رابط الشعار (تم ترجيح الشعار الخاص بصندوق النظافة والتحسين)
LOGO_URL = "https://i.ibb.co/3sZq147/mahrah-clean.jpg"  # رابط الشعار المرفق

# 3. تهيئة البيانات وقواعد البيانات المحلية
if 'trucks' not in st.session_state:
    st.session_state['trucks'] = pd.DataFrame(columns=[
        "رقم السيارة", "نوع السيارة", "الموديل", "حد الصيانة (كم)", 
        "مسافة الدورة الحالية (كم)", "المجموع الشهري (كم)", "تاريخ آخر تغيير زيت"
    ])

if 'daily_logs' not in st.session_state:
    st.session_state['daily_logs'] = pd.DataFrame(columns=["التاريخ", "رقم السيارة", "المسافة اليومية (كم)"])

if 'maintenance_history' not in st.session_state:
    st.session_state['maintenance_history'] = pd.DataFrame(columns=["رقم السيارة", "تاريخ الصيانة", "المسافة عند الصيانة (كم)", "ملاحظات"])

if 'default_limit' not in st.session_state:
    st.session_state['default_limit'] = 2500

if 'warning_ratio' not in st.session_state:
    st.session_state['warning_ratio'] = 90

# 4. الترويسة الزجاجية الفاخرة (Glass Header Bar)
header_html = f"""
<div class="header-glass">
    <div class="header-title-container">
        <img src="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f69b.png" class="logo-img" alt="Logo" style="background: rgba(255,255,255,0.1); padding:10px;">
        <div>
            <h2 style="margin:0; color:#ffffff; font-weight:800; font-size:1.6rem;">صندوق النظافة والتحسين</h2>
            <p style="margin:0; color:#10b981; font-weight:600; font-size:1.05rem;">محافظة المهـرة - نظام متابعة الحركة والزيوت الذكي</p>
        </div>
    </div>
    <div style="text-align: left; color:#94a3b8; font-size:0.9rem;">
        <div>📅 {datetime.now().strftime('%Y-%m-%d')}</div>
        <div style="color:#10b981; font-weight:bold;">🟢 النظام متصل ومحدث</div>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# 5. القائمة الجانبية للتنقل بأيقونات أنيقة
st.sidebar.markdown("""
<div style="text-align:center; padding:10px;">
    <h3 style="color:#ffffff; margin-bottom:5px;">📋 قائمة التحكم</h3>
    <p style="color:#64748b; font-size:0.85rem;">اختر قسم النظام المطلوب</p>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "الانتقال إلى:", 
    [
        "📊 لوحة التحكم الرئيسية", 
        "📥 الحركة اليومية (قراءة الرسائل)", 
        "🛠️ إدارة السيارات والصيانة", 
        "📁 السجل والتصدير لـ Excel", 
        "⚙️ الإعدادات العامة"
    ]
)

# ---------------------------------------------------------
# 📊 1. لوحة التحكم الرئيسية (Dashboard)
# ---------------------------------------------------------
if page == "📊 لوحة التحكم الرئيسية":
    today_str = str(datetime.now().date())
    
    total_trucks = len(st.session_state['trucks'])
    today_logs = st.session_state['daily_logs'][st.session_state['daily_logs']['التاريخ'] == today_str]
    moved_today_count = len(today_logs['رقم السيارة'].unique()) if not today_logs.empty else 0
    today_total_km = today_logs['المسافة اليومية (كم)'].sum() if not today_logs.empty else 0.0

    # حساب السيارات المفحوصة والتنبيهات
    overdue_count = 0
    warning_count = 0
    if not st.session_state['trucks'].empty:
        for _, truck in st.session_state['trucks'].iterrows():
            limit = truck['حد الصيانة (كم)'] if truck['حد الصيانة (كم)'] > 0 else 2500
            current = truck['مسافة الدورة الحالية (كم)']
            ratio = (current / limit) * 100
            if ratio >= 100:
                overdue_count += 1
            elif ratio >= st.session_state['warning_ratio']:
                warning_count += 1

    # عرض الأرقام بطاقات Squircle مرتبة في شبكة
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1:
        st.markdown(f"""
        <div class="squircle-card">
            <div class="card-icon">🚛</div>
            <div class="card-value">{total_trucks}</div>
            <div class="card-label">إجمالي السيارات</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="squircle-card">
            <div class="card-icon">🟢</div>
            <div class="card-value">{moved_today_count}</div>
            <div class="card-label">تحركت اليوم</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="squircle-card">
            <div class="card-icon">📏</div>
            <div class="card-value">{today_total_km:.1f}</div>
            <div class="card-label">مسافة اليوم (كم)</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="squircle-card">
            <div class="card-icon">🟠</div>
            <div class="card-value">{warning_count}</div>
            <div class="card-label">تحتاج صيانة قريباً</div>
        </div>
        """, unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="squircle-card">
            <div class="card-icon">🔴</div>
            <div class="card-value">{overdue_count}</div>
            <div class="card-label">تجاوزت حد الزيت</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # عرض حالة السيارات بصرياً (Progress visualizer)
    st.subheader("🏎️ الحالة الفنية للأسطول ونسب استهلاك الزيت")
    
    if st.session_state['trucks'].empty:
        st.info("💡 لا توجد سيارات مسجلة حالياً في النظام. يمكنك إضافة سيارات من قسم (إدارة السيارات) أو لصق رسالة اليوم لتسجيلها تلقائياً.")
    else:
        for _, truck in st.session_state['trucks'].iterrows():
            t_id = truck['رقم السيارة']
            t_type = truck['نوع السيارة']
            limit = truck['حد الصيانة (كم)'] if truck['حد الصيانة (كم)'] > 0 else 2500
            current = truck['مسافة الدورة الحالية (كم)']
            m_total = truck['المجموع الشهري (كم)']
            
            ratio = min(float(current / limit), 1.0)
            percentage = (current / limit) * 100
            
            col_t1, col_t2, col_t3 = st.columns([1.5, 3.5, 1])
            with col_t1:
                st.markdown(f"**🚛 سيارة #{t_id}** ({t_type})")
                st.caption(f"المجموع الشهري: {m_total:.1f} كم")
            with col_t2:
                st.progress(ratio)
                st.caption(f"المقطوع: **{current:.1f} كم** من أصل **{limit} كم** ({percentage:.1f}%)")
            with col_t3:
                if percentage >= 100:
                    st.error("🔴 تغيير زيت!")
                elif percentage >= st.session_state['warning_ratio']:
                    st.warning("🟠 انتبه!")
                else:
                    st.success("🟢 ممتازة")
            st.markdown("<hr style='margin: 8px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 📥 2. إدخال وتحليل الحركة اليومية
# ---------------------------------------------------------
elif page == "📥 الحركة اليومية (قراءة الرسائل)":
    st.header("📥 تحليل ورصد حركة السيارات اليومية")
    
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        log_date = st.date_input("🗓️ تاريخ الحركة المراد رصدها:", datetime.now())
    with col_d2:
        st.info(f"📌 **سيتم إدراج البيانات المسجلة تحت تاريخ:** `{log_date.strftime('%Y-%m-%d')}`")

    raw_text = st.text_area(
        "ألصق نص كشف الحركة Daily Report هنا:", 
        height=220, 
        placeholder="مثال:\nسيارة رقم 1 المسافة 60.8 كم\nسيارة رقم 2 المسافة 93.1 كم"
    )
    
    if st.button("✨ تحليل واستخراج البيانات ذكياً", type="primary"):
        if not raw_text.strip():
            st.warning("يرجى إدخال أو لصق نص الرسالة أولاً.")
        else:
            # النمط الذهبي المطابق لقراءة المسافات والسيارات باللغة العربية
            pattern = r"(?:سيارة\s*رقم\s*|سيارة\s*)(\d+)(?:[\s\S]*?)(?:المسافة|المسافه|المسافة المقطوعة)\s*([\d\.]+)\s*كم"
            matches = re.findall(pattern, raw_text)
            
            if matches:
                extracted_data = []
                for truck_id, dist in matches:
                    extracted_data.append({
                        "تاريخ الحركة": str(log_date),
                        "رقم السيارة": int(truck_id), 
                        "المسافة اليومية (كم)": float(dist)
                    })

                st.session_state['temp_logs'] = pd.DataFrame(extracted_data)
                st.success(f"🎉 تم التعرف على {len(extracted_data)} سيارة بنجاح!")
            else:
                st.error("لم يتم العثور على صيغ مطابقة. تأكد أن الرسالة تحتوي على (سيارة رقم X المسافة Y كم).")

    # جدول المراجعة قبل الاعتماد
    if 'temp_logs' in st.session_state and not st.session_state['temp_logs'].empty:
        st.subheader("📋 جدول المراجعة والاعتماد النهائي")
        
        edited_df = st.data_editor(st.session_state['temp_logs'], num_rows="dynamic", use_container_width=True)
        
        if st.button("✅ اعتماد وحفظ البيانات بالحافظة"):
            already_logged = 0
            for _, row in edited_df.iterrows():
                t_id = int(row['رقم السيارة'])
                dist = float(row['المسافة اليومية (كم)'])
                entry_date = str(row['تاريخ الحركة'])
                
                # إيقاف التكرار لنفس اليوم والسيارة
                existing = st.session_state['daily_logs'][
                    (st.session_state['daily_logs']['التاريخ'] == entry_date) & 
                    (st.session_state['daily_logs']['رقم السيارة'] == t_id)
                ]
                
                if not existing.empty:
                    already_logged += 1
                    continue

                # حفظ في السجل اليومي
                new_log = pd.DataFrame([{"التاريخ": entry_date, "رقم السيارة": t_id, "المسافة اليومية (كم)": dist}])
                st.session_state['daily_logs'] = pd.concat([st.session_state['daily_logs'], new_log], ignore_index=True)
                
                # إضافة السيارة لقائمة السيارات إن لم تكن موجودة
                existing_trucks = st.session_state['trucks']['رقم السيارة'].tolist() if not st.session_state['trucks'].empty else []
                
                if t_id not in existing_trucks:
                    new_truck = pd.DataFrame([{
                        "رقم السيارة": t_id, 
                        "نوع السيارة": "ضاغطة", 
                        "الموديل": "2024", 
                        "حد الصيانة (كم)": st.session_state['default_limit'], 
                        "مسافة الدورة الحالية (كم)": 0.0, 
                        "المجموع الشهري (كم)": 0.0, 
                        "تاريخ آخر تغيير زيت": "لم يسجل"
                    }])
                    st.session_state['trucks'] = pd.concat([st.session_state['trucks'], new_truck], ignore_index=True)

                # تحديث المسافات والتنبيهات
                truck_idx = st.session_state['trucks'].index[st.session_state['trucks']['رقم السيارة'] == t_id][0]
                limit = st.session_state['trucks'].loc[truck_idx, 'حد الصيانة (كم)']
                current_km = st.session_state['trucks'].loc[truck_idx, 'مسافة الدورة الحالية (كم)']
                
                new_km = current_km + dist
                if new_km >= limit:
                    overflow = new_km - limit
                    st.session_state['trucks'].loc[truck_idx, 'مسافة الدورة الحالية (كم)'] = overflow
                    st.warning(f"🚨 السيارة رقم {t_id} تجاوزت حد الصيانة ({limit} كم)! تم بدء دورة جديدة برصيد {overflow:.1f} كم.")
                else:
                    st.session_state['trucks'].loc[truck_idx, 'مسافة الدورة الحالية (كم)'] = new_km
                    
                st.session_state['trucks'].loc[truck_idx, 'المجموع الشهري (كم)'] += dist
            
            if already_logged > 0:
                st.info(f"تم تخطي {already_logged} سجل مسجل مسبقاً بنفس التاريخ.")
            st.success(f"تم حفظ الحركة اليومية بنجاح لتاريخ {log_date}!")
            del st.session_state['temp_logs']

# ---------------------------------------------------------
# 🛠️ 3. إدارة السيارات والصيانة
# ---------------------------------------------------------
elif page == "🛠️ إدارة السيارات والصيانة":
    st.header("🛠️ صيانة السيارات والدورات")
    
    t1, t2, t3 = st.tabs(["📋 الأسطول المسجل", "➕ إضافة / تعديل سيارة", "🛢️ توثيق تغيير الزيت"])
    
    with t1:
        st.dataframe(st.session_state['trucks'], use_container_width=True)
        
    with t2:
        col_a, col_b, col_c = st.columns(3)
        new_id = col_a.number_input("رقم السيارة:", min_value=1, step=1)
        new_type = col_b.text_input("نوع السيارة:", value="ضاغطة")
        new_model = col_c.text_input("الموديل:", value="2024")
        custom_limit = st.number_input("حد غيار الزيت (كم):", value=st.session_state['default_limit'], step=100)
        
        if st.button("حفظ بيانات السيارة"):
            existing_ids = st.session_state['trucks']['رقم السيارة'].tolist() if not st.session_state['trucks'].empty else []
            if new_id in existing_ids:
                idx = st.session_state['trucks'].index[st.session_state['trucks']['رقم السيارة'] == new_id][0]
                st.session_state['trucks'].loc[idx, 'نوع السيارة'] = new_type
                st.session_state['trucks'].loc[idx, 'الموديل'] = new_model
                st.session_state['trucks'].loc[idx, 'حد الصيانة (كم)'] = custom_limit
                st.success(f"تم تحديث بيانات السيارة رقم #{new_id}!")
            else:
                new_row = pd.DataFrame([{
                    "رقم السيارة": new_id, 
                    "نوع السيارة": new_type, 
                    "الموديل": new_model, 
                    "حد الصيانة (كم)": custom_limit, 
                    "مسافة الدورة الحالية (كم)": 0.0, 
                    "المجموع الشهري (كم)": 0.0, 
                    "تاريخ آخر تغيير زيت": "لم يسجل"
                }])
                st.session_state['trucks'] = pd.concat([st.session_state['trucks'], new_row], ignore_index=True)
                st.success(f"تم إضافة السيارة رقم #{new_id} بنجاح!")

    with t3:
        if not st.session_state['trucks'].empty:
            t_id = st.selectbox("اختر السيارة لإجراء تغيير الزيت:", st.session_state['trucks']['رقم السيارة'].tolist())
            service_date = st.date_input("تاريخ تغيير الزيت:", datetime.now())
            notes = st.text_input("ملاحظات ورقم الفاتورة:")
            
            if st.button("إتمام تغيير الزيت وتصفير العداد للحساب من 0"):
                truck_idx = st.session_state['trucks'].index[st.session_state['trucks']['رقم السيارة'] == t_id][0]
                current_km = st.session_state['trucks'].loc[truck_idx, 'مسافة الدورة الحالية (كم)']
                
                # إضافة لسجل الصيانة
                new_record = pd.DataFrame([{"رقم السيارة": t_id, "تاريخ الصيانة": str(service_date), "المسافة عند الصيانة (كم)": current_km, "ملاحظات": notes}])
                st.session_state['maintenance_history'] = pd.concat([st.session_state['maintenance_history'], new_record], ignore_index=True)
                
                # تصفير الدورة
                st.session_state['trucks'].loc[truck_idx, 'مسافة الدورة الحالية (كم)'] = 0.0
                st.session_state['trucks'].loc[truck_idx, 'تاريخ آخر تغيير زيت'] = str(service_date)
                st.success(f"تم تصفير الدورة وتوثيق تغيير الزيت للسيارة #{t_id} بنجاح!")
        else:
            st.info("لا توجد سيارات مسجلة حالياً.")

# ---------------------------------------------------------
# 📁 4. السجل والأرشيف وتصدير Excel
# ---------------------------------------------------------
elif page == "📁 السجل والتصدير لـ Excel":
    st.header("📁 الأرشيف الشهري والتصدير")
    
    st.subheader("سجل الحركة اليومي الكامل")
    st.dataframe(st.session_state['daily_logs'], use_container_width=True)
    
    # التصدير المباشر لملف Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state['daily_logs'].to_excel(writer, sheet_name='الحركة اليومية', index=False)
        st.session_state['trucks'].to_excel(writer, sheet_name='السيارات والدورات', index=False)
        st.session_state['maintenance_history'].to_excel(writer, sheet_name='أرشيف تغيير الزيت', index=False)
        
    st.download_button(
        label="📥 تصدير التقرير الشامل كملف (Excel)",
        data=buffer.getvalue(),
        file_name=f"تقرير_صندوق_النظافة_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )

# ---------------------------------------------------------
# ⚙️ 5. الإعدادات العامة
# ---------------------------------------------------------
elif page == "⚙️ الإعدادات العامة":
    st.header("⚙️ إعدادات النظام وتنبيهات الزيت")
    
    st.session_state['default_limit'] = st.number_input("حد الزيت الافتراضي (كم):", value=st.session_state['default_limit'], step=100)
    st.session_state['warning_ratio'] = st.slider("نسبة التنبيه قبل وصول الحد (%):", min_value=50, max_value=98, value=st.session_state['warning_ratio'])
    
    st.success("تم تطبيق الإعدادات الحالية بنجاح.")
