# دليل أفضل الممارسات - تطبيق إدارة الأسطول

## 🚀 نصائح متقدمة للمطورين

### **1. إدارة الأخطاء والاستثناءات**

#### ✅ **افعل:**
```python
# معالجة محددة لكل نوع استثناء
try:
    result = some_operation()
except ValueError as e:
    logger.error(f"قيمة غير صحيحة: {e}")
except ConnectionError as e:
    logger.error(f"مشكلة في الاتصال: {e}")
except Exception as e:
    logger.error(f"خطأ غير متوقع: {e}", exc_info=True)
```

#### ❌ **لا تفعل:**
```python
# تجنب الاستثناء العام
try:
    result = some_operation()
except Exception:
    pass  # يخفي الأخطاء الخطيرة
```

---

### **2. تحسين الأداء**

#### ✅ **استخدم التخزين المؤقت بحكمة:**
```python
# للعمليات الثقيلة التي لا تتغير كثيراً
@st.cache_data(ttl=300, show_spinner=False)
def expensive_operation(data):
    # معالجة ثقيلة
    return result
```

#### ✅ **تجنب العمليات المتكررة:**
```python
# ❌ سيء: يُحسب في كل مرة
for row in df.iterrows():
    heavy_calculation(row)

# ✅ جيد: يُحسب مرة واحدة
preprocessed = preprocess_data(df)
for row in preprocessed.iterrows():
    light_calculation(row)
```

---

### **3. الأمان**

#### ✅ **التحقق من البيانات دائماً:**
```python
# لا تثق بأي إدخال من المستخدم
def save_record(data):
    # التحقق قبل الحفظ
    if not validate_record(data):
        raise ValueError("بيانات غير صحيحة")
    # تنظيف النصوص
    data['details'] = sanitize_text(data['details'])
    # الحفظ
    storage.save(data)
```

#### ✅ **لا تخزن أسراراً في الكود:**
```python
# ❌ سيء جداً
API_KEY = "sk-1234567890abcdef"

# ✅ جيد
API_KEY = st.secrets.get("api_key")
```

---

### **4. التعامل مع Google Sheets API**

#### ✅ **تعيين timeout للاتصال:**
```python
import socket
socket.setdefaulttimeout(30)  # 30 ثانية
try:
    client = gspread.service_account(...)
finally:
    socket.setdefaulttimeout(None)
```

#### ✅ **تجنب طلبات API المتكررة:**
```python
# ❌ سيء: طلب لكل سجل
for record in records:
    sheet.append_row(record)

# ✅ جيد: طلب واحد للدفعة الكاملة
sheet.append_rows(records)
```

---

### **5. تجربة المستخدم (UX)**

#### ✅ **قدم رسائل واضحة:**
```python
# أخطاء محددة
if error_type == "network":
    st.error("تعذر الاتصال بالخادم. تحقق من الإنترنت.")
elif error_type == "validation":
    st.error("البيانات المدخلة غير صحيحة.")
```

#### ✅ **استخدم أزرار التأكيد للعمليات الخطرة:**
```python
if st.checkbox("أؤيد حذف هذه البيانات"):
    if st.button("حذف نهائي", type="primary"):
        delete_data()
```

---

### **6. الكتابة على Git**

#### ✅ **تجاهل الملفات الحساسة:**
```gitignore
# .gitignore
.streamlit/secrets.toml
data/
*.csv
__pycache__/
```

#### ✅ **رسائل commit واضحة:**
```bash
# ✅ جيد
git commit -m "إضافة التحقق من صحة التواريخ"

# ❌ سيء
git commit -m "fix"
```

---

### **7. الاختبار**

#### ✅ **اكتب اختبارات للدوال الحرجة:**
```python
def test_oil_counter():
    # اختبار الحدود
    counter, reached, _ = add_distance(2400, 2500, 100)
    assert counter == 2500  # لا يتجاوز الحد
    assert reached is True
```

#### ✅ **اختبر السيناريوهات الحدية:**
```python
# اختبار قيم الحدود
test_cases = [
    (0, 2500, 2500),  # الوصول للحد بالضبط
    (2500, 2500, 100),  # التجاوز
    (-10, 2500, 100),  # قيم سالبة
]
```

---

### **8. التوثيق**

#### ✅ **استخدم docstrings:**
```python
def calculate_oil_cycle(counter: float, limit: float) -> dict:
    """
    يحسب حالة دورة الزيت الحالية.

    Args:
        counter: العداد الحالي
        limit: حد تغيير الزيت

    Returns:
        dict يحتوي على: counter, limit, status, remaining
    """
    # الكود
```

#### ✅ **أضف تعليقات للمنطق المعقد:**
```python
# نستخدم hash SHA256 لمنع تكرار حفظ نفس الدفعة
# حتى لو ضغط المستخدم على الزر مرتين بسرعة
signature = hashlib.sha256(data.encode()).hexdigest()
```

---

### **9. التعامل مع البيانات الكبيرة**

#### ✅ **استخدم الفلترة قبل المعالجة:**
```python
# ❌ سيء: معالجة كل البيانات
processed = process_all_data(df)

# ✅ جيد: فلترة أولاً
recent = df[df['date'] > '2024-01-01']
processed = process_data(recent)
```

#### ✅ **استخدم chunking للبيانات الضخمة:**
```python
chunk_size = 1000
for i in range(0, len(data), chunk_size):
    chunk = data[i:i+chunk_size]
    process_chunk(chunk)
```

---

### **10. التصحيح (Debugging)**

#### ✅ **استخدم logging بدلاً من print:**
```python
# ❌ سيء للإنتاج
print(f"Processing: {data}")

# ✅ جيد
logger.info(f"Processing {len(data)} records")
logger.debug(f"Data sample: {data.head()}")
```

#### ✅ **استخدم أدوات Streamlit للتصحيح:**
```python
# عرض متغيرات مؤقتة
st.json(session_state)

# قياس الأداء
import time
start = time.time()
result = expensive_function()
st.write(f"Time: {time.time() - start:.2f}s")
```

---

## 📊 مقاييس الأداء الموصى بها

- **وقت تحميل الصفحة:** < 3 ثواني
- **وقت حفظ البيانات:** < 5 ثواني
- **استهلاك الذاكرة:** < 500 MB
- **حجم الصفحة:** < 2 MB

---

## 🔧 أدوات مفيدة

```bash
# فحص جودة الكود
pip install pylint
pylint fleet/

# فحص الأمان
pip install bandit
bandit -r fleet/

# اختبار التغطية
pip install pytest-cov
pytest --cov=fleet tests/
```

---

## 📚 موارد إضافية

- [Streamlit Best Practices](https://docs.streamlit.io/library/advanced-features/caching)
- [Python Logging Guide](https://docs.python.org/3/howto/logging.html)
- [Google Sheets API Best Practices](https://developers.google.com/sheets/api/guides/performance)
