import streamlit as st
import pandas as pd
import re
from datetime import datetime
import io

# ضبط إعدادات الصفحة لتكون متجاوبة مع الجوال واللابتوب
st.set_page_config(page_title="نظام إدارة سيارات النظافة", page_icon="🚛", layout="wide")

# تهيئة قاعدة البيانات المحلية في الجلسة (Session State)
if 'trucks' not in st.session_state:
    # البداية الافتراضية بـ 18 سيارة مع إمكانية التعديل والإضافة بلا حدود
    st.session_state['trucks'] = pd.DataFrame([
        {"id": i, "type": "ضاغطة", "model": "2024", "limit": 2500, "current_cycle_km": 0.0, "monthly_km": 0.0, "last_oil_change": "لم يسجل"}
        for i in range(1, 19)
    ])

if 'daily_logs' not in st.session_state:
    st.session_state['daily_logs'] = pd.DataFrame(columns=["date", "truck_id", "distance_km"])

if 'maintenance_history' not in st.session_state:
    st.session_state['maintenance_history'] = pd.DataFrame(columns=["truck_id", "date", "km_at_service", "notes"])

if 'default_limit' not in st.session_state:
    st.session_state['default_limit'] = 2500

if 'warning_ratio' not in st.session_state:
    st.session_state['warning_ratio'] = 90

# القائمة الجانبية للتنقل
st.sidebar.title("🚛 صندوق النظافة والتحسين")
page = st.sidebar.radio("الانتقال إلى:", [
    "لوحة التحكم الرئيسية", 
    "الحركة اليومية (إدخال الرسالة)", 
    "إدارة السيارات والصيانة", 
    "السجل والأرشيف الشهري", 
    "الإعدادات"
])

# ---------------------------------------------------------
# 1. صفحة الحركة اليومية (إدخال الرسالة وتحليلها)
# ---------------------------------------------------------
if page == "الحركة اليومية (إدخال الرسالة)":
    st.header("📥 إدخال الحركة اليومية")
    
    log_date = st.date_input("تاريخ الحركة:", datetime.now())
    raw_text = st.text_area("ألصق رسالة الحركة اليومية هنا:", height=200, placeholder="سيارة رقم 1\nالمسافة 60.8 كم\n...")
    
    if st.button("🔍 تحليل الرسالة", type="primary"):
        if not raw_text.strip():
            st.warning("يرجى لصق نص الرسالة أولاً.")
        else:
            # نمط المطابقة لإنعكاس مختلف كتابات كلمة المسافة وأرقام السيارات
            pattern = r"(?:سيارة\s*رقم\s*|سيارة\s*)(\d+)(?:[\s\S]*?)(?:المسافة|المسافه|المسافة المقطوعة)\s*([\d\.]+)\s*كم"
            matches = re.findall(pattern, raw_text)
            
            if matches:
                extracted_data = []
                existing_ids = st.session_state['trucks']['id'].tolist()
                
                for truck_id, dist in matches:
                    t_id = int(truck_id)
                    extracted_data.append({"truck_id": t_id, "distance_km": float(dist)})
                    
                    # إذا كانت السيارة غير مسجلة مسبقاً يتم إضافتها تلقائياً للأسطول
                    if t_id not in existing_ids:
                        new_truck = pd.DataFrame([{
                            "id": t_id, 
                            "type": "جديدة", 
                            "model": "-", 
                            "limit": st.session_state['default_limit'], 
                            "current_cycle_km": 0.0, 
                            "monthly_km": 0.0, 
                            "last_oil_change": "لم يسجل"
                        }])
                        st.session_state['trucks'] = pd.concat([st.session_state['trucks'], new_truck], ignore_index=True)
                        existing_ids.append(t_id)
                        st.info(f"✨ تم اكتشاف وإضافة سيارة جديدة تلقائياً برقم: {t_id}")

                st.session_state['temp_logs'] = pd.DataFrame(extracted_data)
                st.success(f"تم استخراج بيانات {len(extracted_data)} سيارة بنجاح!")
            else:
                st.error("لم يتم العثور على بيانات مطابقة. تأكد من إدراج رقم السيارة والمسافة.")

    # عرض البيانات المستخرجة للمراجعة والتعديل قبل الاعتماد النهائي
    if 'temp_logs' in st.session_state and not st.session_state['temp_logs'].empty:
        st.subheader("📋 مراجعة البيانات قبل الاعتماد")
        
        edited_df = st.data_editor(st.session_state['temp_logs'], num_rows="dynamic", use_container_width=True)
        
        if st.button("✅ اعتماد البيانات وحفظها"):
            already_logged_count = 0
            for _, row in edited_df.iterrows():
                t_id = int(row['truck_id'])
                dist = float(row['distance_km'])
                
                # التحقق من التكرار لنفس اليوم
                existing = st.session_state['daily_logs'][
                    (st.session_state['daily_logs']['date'] == str(log_date)) & 
                    (st.session_state['daily_logs']['truck_id'] == t_id)
                ]
                
                if not existing.empty:
                    already_logged_count += 1
                    continue

                # حفظ الحركة اليومية
                new_log = pd.DataFrame([{"date": str(log_date), "truck_id": t_id, "distance_km": dist}])
                st.session_state['daily_logs'] = pd.concat([st.session_state['daily_logs'], new_log], ignore_index=True)
                
                # تحديث دورة الصيانة والمجموع الشهري للسيارة
                truck_idx_list = st.session_state['trucks'].index[st.session_state['trucks']['id'] == t_id].tolist()
                if truck_idx_list:
                    idx = truck_idx_list[0]
                    limit = st.session_state['trucks'].loc[idx, 'limit']
                    current_km = st.session_state['trucks'].loc[idx, 'current_cycle_km']
                    
                    new_km = current_km + dist
                    # التعامل مع تجاوز حد الصيانة
                    if new_km >= limit:
                        overflow = new_km - limit
                        st.session_state['trucks'].loc[idx, 'current_cycle_km'] = overflow
                        st.warning(f"🚨 السيارة رقم {t_id} وصلت/تجاوزت حد الصيانة ({limit} كم)! بدأت دورة جديدة بـ {overflow:.1f} كم.")
                    else:
                        st.session_state['trucks'].loc[idx, 'current_cycle_km'] = new_km
                        
                    st.session_state['trucks'].loc[idx, 'monthly_km'] += dist
            
            if already_logged_count > 0:
                st.info(f"تم تجاهل {already_logged_count} سجل/سجلات نظراً لتسجيلها مسبقاً في هذا التاريخ.")
            st.success("تم اعتماد البيانات وتحديث الدورة والمجاميع بنجاح!")
            del st.session_state['temp_logs']

# ---------------------------------------------------------
# 2. لوحة التحكم الرئيسية (Dashboard)
# ---------------------------------------------------------
elif page == "لوحة التحكم الرئيسية":
    st.header("📊 لوحة التحكم الرئيسية")
    
    total_trucks = len(st.session_state['trucks'])
    today_str = str(datetime.now().date())
    today_logs = st.session_state['daily_logs'][st.session_state['daily_logs']['date'] == today_str]
    moved_today_count = len(today_logs['truck_id'].unique()) if not today_logs.empty else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي السيارات المسجلة", total_trucks)
    col2.metric("تحركت اليوم", moved_today_count)
    col3.metric("لم تظهر اليوم", total_trucks - moved_today_count)
    col4.metric("إجمالي مسافات اليوم", f"{today_logs['distance_km'].sum():.1f} كم" if not today_logs.empty else "0.0 كم")

    st.markdown("---")
    st.subheader("🚨 حالة التنبيهات والصيانة")
    
    has_alerts = False
    for _, truck in st.session_state['trucks'].iterrows():
        limit = truck['limit'] if truck['limit'] > 0 else 2500
        ratio = (truck['current_cycle_km'] / limit) * 100
        if ratio >= 100:
            has_alerts = True
            st.error(f"🔴 السيارة رقم {truck['id']}: وصلت إلى حد الصيانة ({truck['current_cycle_km']:.1f} / {limit} كم)")
        elif ratio >= st.session_state['warning_ratio']:
            has_alerts = True
            st.warning(f"🟠 السيارة رقم {truck['id']}: اقتربت من حد الصيانة ({truck['current_cycle_km']:.1f} / {limit} كم - {ratio:.1f}%)")
            
    if not has_alerts:
        st.success("🟢 جميع السيارات في حالة ممتازة ولم تصل أي سيارة إلى حد التنبيه.")

# ---------------------------------------------------------
# 3. إدارة السيارات وتسجيل تغيير الزيت
# ---------------------------------------------------------
elif page == "إدارة السيارات والصيانة":
    st.header("🛠️ إدارة أسطول السيارات والتعديل والصيانة")
    
    tab1, tab2, tab3 = st.tabs(["قائمة السيارات الحالية", "➕ إضافة / تعديل سيارة", "🛢️ تسجيل تغيير زيت"])
    
    with tab1:
        st.subheader("السيارات المسجلة حالياً")
        st.dataframe(st.session_state['trucks'], use_container_width=True)
        
    with tab2:
        st.subheader("إضافة سيارة جديدة أو تعديل سيارة موجودة")
        col_a, col_b, col_c = st.columns(3)
        new_id = col_a.number_input("رقم السيارة:", min_value=1, step=1)
        new_type = col_b.text_input("نوع السيارة:", value="ضاغطة")
        new_model = col_c.text_input("الموديل:", value="2024")
        custom_limit = st.number_input("حد الصيانة لهذه السيارة (كم):", value=st.session_state['default_limit'], step=100)
        
        if st.button("حفظ / إضافة السيارة"):
            existing_ids = st.session_state['trucks']['id'].tolist()
            if new_id in existing_ids:
                # تعديل البيانات
                idx = st.session_state['trucks'].index[st.session_state['trucks']['id'] == new_id][0]
                st.session_state['trucks'].loc[idx, 'type'] = new_type
                st.session_state['trucks'].loc[idx, 'model'] = new_model
                st.session_state['trucks'].loc[idx, 'limit'] = custom_limit
                st.success(f"تم تحديث بيانات السيارة رقم {new_id} بنجاح!")
            else:
                # إضافة سيارة جديدة
                new_row = pd.DataFrame([{
                    "id": new_id, 
                    "type": new_type, 
                    "model": new_model, 
                    "limit": custom_limit, 
                    "current_cycle_km": 0.0, 
                    "monthly_km": 0.0, 
                    "last_oil_change": "لم يسجل"
                }])
                st.session_state['trucks'] = pd.concat([st.session_state['trucks'], new_row], ignore_index=True)
                st.success(f"تم إضافة السيارة رقم {new_id} بنجاح!")

    with tab3:
        st.subheader("تسجيل صيانة جديدة")
        if not st.session_state['trucks'].empty:
            t_id = st.selectbox("اختر السيارة:", st.session_state['trucks']['id'].tolist())
            service_date = st.date_input("تاريخ تغيير الزيت:", datetime.now())
            notes = st.text_input("ملاحظات (نوع الزيت، رقم الفاتورة...):")
            
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
    
    new_limit = st.number_input("حد دورة الصيانة الافتراضي للسيارات الجديدة (كم):", value=st.session_state['default_limit'], step=100)
    new_warning = st.slider("نسبة التنبيه المبكر (%):", min_value=50, max_value=95, value=st.session_state['warning_ratio'])
    
    if st.button("حفظ الإعدادات"):
        st.session_state['default_limit'] = new_limit
        st.session_state['warning_ratio'] = new_warning
        st.success("تم تحديث الإعدادات الافتراضية بنجاح.")
