import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io

# ضبط إعدادات الصفحة لتكون متجاوبة مع الجوال واللابتوب
st.set_page_config(page_title="نظام إدارة سيارات النظافة", page_icon="🚛", layout="wide")

# تهيئة قاعدة البيانات المحلية في الجلسة (Session State)
if 'trucks' not in st.get_states():
    st.session_state['trucks'] = pd.DataFrame([
        {"id": i, "type": "ضاغطة", "limit": 2500, "current_cycle_km": 0.0, "monthly_km": 0.0, "last_oil_change": "لم يسجل"}
        for i in range(1, 19)
    ])

if 'daily_logs' not in st.get_states():
    st.session_state['daily_logs'] = pd.DataFrame(columns=["date", "truck_id", "distance_km"])

if 'maintenance_history' not in st.get_states():
    st.session_state['maintenance_history'] = pd.DataFrame(columns=["truck_id", "date", "km_at_service", "notes"])

if 'warning_ratio' not in st.get_states():
    st.session_state['warning_ratio'] = 90

# القائمة الجانبية للتنقل (تظهر كقائمة منسدلة في الجوال)
st.sidebar.title("🚛 صندوق النظافة والتحسين")
page = st.sidebar.radio("الانتقال إلى:", [
    "لوحة التحكم الرئيسية", 
    "الحركة اليومية (إدخال الرسالة)", 
    "السيارات والصيانة", 
    "السجل والأرشيف الشهري", 
    "الإعدادات"
])

# ---------------------------------------------------------
# 1. صفحة الحركة اليومية (إدخال الرسالة وتحليلها)
# ---------------------------------------------------------
if page == "الحركة اليومية (إدخال الرسالة)":
    st.header("📥 إدخال الحركة اليومية")
    
    log_date = st.date_input("تاريخ الحركة:", datetime.now())
    raw_text = st.text_area("أصق رسالة الحركة اليومية هنا:", height=200, placeholder="سيارة رقم 1\nالمسافة 60.8 كم\n...")
    
    if st.button("🔍 تحليل الرسالة", type="primary"):
        if not raw_text.strip():
            st.warning("يرجى لصق نص الرسالة أولاً.")
        else:
            # نمط المطابقة يستخرج رقم السيارة والمسافة بغض النظر عن طريقة كتابة كلمة المسافة
            pattern = r"(?:سيارة\s*رقم\s*|سيارة\s*)(\d+)(?:[\s\S]*?)(?:المسافة|المسافه|المسافة المقطوعة)\s*([\d\.]+)\s*كم"
            matches = re.findall(pattern, raw_text)
            
            if matches:
                extracted_data = []
                for truck_id, dist in matches:
                    extracted_data.append({"truck_id": int(truck_id), "distance_km": float(dist)})
                
                st.session_state['temp_logs'] = pd.DataFrame(extracted_data)
                st.success(f"تم استخراج بيانات {len(extracted_data)} سيارة بنجاح!")
            else:
                st.error("لم يتم العثور على بيانات مطابقة. تأكد من أن الرسالة تحتوي على رقم السيارة والمسافة بـ كم.")

    # عرض البيانات المستخرجة للمراجعة والتعديل قبل الاعتماد النهائي
    if 'temp_logs' in st.session_state and not st.session_state['temp_logs'].empty:
        st.subheader("📋 مراجعة البيانات قبل الاعتماد")
        
        # إمكانية تعديل الجدول مباشرة
        edited_df = st.data_editor(st.session_state['temp_logs'], num_rows="dynamic", use_container_width=True)
        
        if st.button("✅ اعتماد البيانات وحفظها"):
            already_logged = False
            for _, row in edited_df.iterrows():
                t_id = int(row['truck_id'])
                dist = float(row['distance_km'])
                
                # التحقق من التكرار لنفس اليوم
                existing = st.session_state['daily_logs'][
                    (st.session_state['daily_logs']['date'] == str(log_date)) & 
                    (st.session_state['daily_logs']['truck_id'] == t_id)
                ]
                
                if not existing.empty:
                    already_logged = True
                    continue

                # حفظ الحركة اليومية
                new_log = pd.DataFrame([{"date": str(log_date), "truck_id": t_id, "distance_km": dist}])
                st.session_state['daily_logs'] = pd.concat([st.session_state['daily_logs'], new_log], ignore_index=True)
                
                # تحديث دورة الصيانة والمجموع الشهري للسيارة
                truck_idx = st.session_state['trucks'].index[st.session_state['trucks']['id'] == t_id].tolist()
                if truck_idx:
                    idx = truck_idx[0]
                    limit = st.session_state['trucks'].loc[idx, 'limit']
                    current_km = st.session_state['trucks'].loc[idx, 'current_cycle_km']
                    
                    # حساب تجاوز حد الـ 2500 كم
                    new_km = current_km + dist
                    if new_km >= limit:
                        overflow = new_km - limit
                        st.session_state['trucks'].loc[idx, 'current_cycle_km'] = overflow
                        st.warning(f"🚨 السيارة رقم {t_id} تجاوزت حد الصيانة ({limit} كم)! بدأت دورة جديدة بـ {overflow:.1f} كم.")
                    else:
                        st.session_state['trucks'].loc[idx, 'current_cycle_km'] = new_km
                        
                    st.session_state['trucks'].loc[idx, 'monthly_km'] += dist
            
            if already_logged:
                st.info("بعض البيانات كانت مسجلة مسبقاً لهذا التاريخ وتم تجاهل تكرارها.")
            else:
                st.success("تم اعتماد البيانات وتحديث الحسابات ودورات الصيانة بنجاح!")
            
            del st.session_state['temp_logs']

# ---------------------------------------------------------
# 2. لوحة التحكم الرئيسية (Dashboard)
# ---------------------------------------------------------
elif page == "لوحة التحكم الرئيسية":
    st.header("📊 لوحة التحكم الرئيسية")
    
    col1, col2, col3, col4 = st.columns(4)
    total_trucks = len(st.session_state['trucks'])
    today_str = str(datetime.now().date())
    moved_today = len(st.session_state['daily_logs'][st.session_state['daily_logs']['date'] == today_str])
    
    col1.metric("إجمالي السيارات", total_trucks)
    col2.metric("تحركت اليوم", moved_today)
    col3.metric("لم تظهر اليوم", total_trucks - moved_today)
    col4.metric("إجمالي مسافات اليوم", f"{st.session_state['daily_logs'][st.session_state['daily_logs']['date'] == today_str]['distance_km'].sum():.1f} كم")

    st.markdown("---")
    st.subheader("🚨 حالة التنبيهات والصيانة")
    
    # مصفوفة التنبيهات للسيارات القريبة من حد الصيانة أو التي تجاوزته
    for _, truck in st.session_state['trucks'].iterrows():
        ratio = (truck['current_cycle_km'] / truck['limit']) * 100
        if ratio >= 100:
            st.error(f"🔴 السيارة رقم {truck['id']}: وصلت إلى حد الصيانة ({truck['current_cycle_km']:.1f} / {truck['limit']} كم)")
        elif ratio >= st.session_state['warning_ratio']:
            st.warning(f"🟠 السيارة رقم {truck['id']}: اقتربت من حد الصيانة ({truck['current_cycle_km']:.1f} / {truck['limit']} كم - {ratio:.1f}%)")

# ---------------------------------------------------------
# 3. إدارة السيارات وتسجيل تغيير الزيت
# ---------------------------------------------------------
elif page == "السيارات والصيانة":
    st.header("🛠️ إدارة السيارات وتسجيل تغيير الزيت")
    
    tab1, tab2 = st.tabs(["قائمة السيارات", "تسجيل تغيير زيت"])
    
    with tab1:
        st.dataframe(st.session_state['trucks'], use_container_width=True)
        
    with tab2:
        st.subheader("تسجيل صيانة جديدة")
        t_id = st.selectbox("اختر السيارة:", st.session_state['trucks']['id'].tolist())
        service_date = st.date_input("تاريخ تغيير الزيت:", datetime.now())
        notes = st.text_input("ملاحظات (نوع الزيت، الفاتورة...):")
        
        if st.button("إتمام تغيير الزيت وبدء دورة جديدة من 0 كم"):
            truck_idx = st.session_state['trucks'].index[st.session_state['trucks']['id'] == t_id][0]
            current_km = st.session_state['trucks'].loc[truck_idx, 'current_cycle_km']
            
            # تسجيل الصيانة في السجل
            new_record = pd.DataFrame([{"truck_id": t_id, "date": str(service_date), "km_at_service": current_km, "notes": notes}])
            st.session_state['maintenance_history'] = pd.concat([st.session_state['maintenance_history'], new_record], ignore_index=True)
            
            # إعادة تصفير الدورة
            st.session_state['trucks'].loc[truck_idx, 'current_cycle_km'] = 0.0
            st.session_state['trucks'].loc[truck_idx, 'last_oil_change'] = str(service_date)
            st.success(f"تم تسجيل تغيير الزيت للسيارة رقم {t_id} وبدء دورة جديدة من 0 كم.")

# ---------------------------------------------------------
# 4. السجل الأرشيفي والتصدير لـ Excel
# ---------------------------------------------------------
elif page == "السجل والأرشيف الشهري":
    st.header("📁 السجل التاريخي والتصدير")
    
    st.subheader("سجل الحركة اليومية")
    st.dataframe(st.session_state['daily_logs'], use_container_width=True)
    
    # التصدير إلى Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state['daily_logs'].to_excel(writer, sheet_name='الحركة اليومية', index=False)
        st.session_state['trucks'].to_excel(writer, sheet_name='السيارات والدورات', index=False)
        st.session_state['maintenance_history'].to_excel(writer, sheet_name='سجل تغيير الزيت', index=False)
        
    st.download_button(
        label="📥 تصدير التقرير الشامل إلى Excel",
        data=buffer.getvalue(),
        file_name=f"تقرير_حركة_النظافة_{datetime.now().strftime('%Y_%m')}.xlsx",
        mime="application/vnd.ms-excel"
    )

# ---------------------------------------------------------
# 5. الإعدادات العامة
# ---------------------------------------------------------
elif page == "الإعدادات":
    st.header("⚙️ إعدادات النظام")
    
    new_limit = st.number_input("حد دورة الصيانة الافتراضي (كم):", value=2500, step=100)
    new_warning = st.slider("نسبة التنبيه المبكر (%):", min_value=50, max_value=95, value=st.session_state['warning_ratio'])
    
    if st.button("حفظ الإعدادات"):
        st.session_state['warning_ratio'] = new_warning
        st.session_state['trucks']['limit'] = new_limit
        st.success("تم تحديث الإعدادات وتعميم حد الصيانة الجديد على جميع السيارات.")
