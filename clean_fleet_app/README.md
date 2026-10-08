# تطبيق إدارة أسطول الشاحنات والزيوت
صندوق النظافة والتحسين - محافظة المهرة

## المتطلبات

- Python 3.9 أو أحدث
- المكتبات المطلوبة (انظر requirements.txt)

## التثبيت

```bash
pip install -r requirements.txt
```

## التشغيل

```bash
streamlit run app.py
```

## إعداد Google Sheets (مطلوب للإنتاج)

1. أنشئ مشروعاً في [Google Cloud Console](https://console.cloud.google.com/)
2. فعّل Google Sheets API و Google Drive API
3. أنشئ حساب خدمة (Service Account) وحمّل ملف JSON
4. انسخ محتوى ملف JSON إلى `.streamlit/secrets.toml`

مثال لملف `secrets.toml`:

```toml
[gcp_service_account]
project_id = "your-project-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_KEY_HERE\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"

[gsheets]
spreadsheet_id = ""  # يُترك فارغاً للإنشاء التلقائي
share_with = "email@example.com"
```

**مهم:** استخدم الملف `secrets.toml.example` كمرجع.

## الأمان

- لا ترفع أبداً ملف `secrets.toml` إلى Git
- تأكد من أن حساب الخدمة له صلاحية Editor على جدول البيانات
- في بيئة التطوير المحلية، يمكنك تعيين متغير البيئة:
  ```bash
  export FLEET_ALLOW_LOCAL_STORAGE=1
  ```

## الاختبارات

```bash
# اختبار المنطق الأساسي
python tests/test_core.py

# اختبار واجهة المستخدم
python tests/test_app_ui.py
```

## هيكل المشروع

```
clean_fleet_app/
├── app.py                 # التطبيق الرئيسي
├── fleet/                 # الحزم الداخلية
│   ├── analytics.py       # التحليلات والرسوم
│   ├── config.py          # الإعدادات والثوابت
│   ├── oil.py             # محرك حساب عداد الزيت
│   ├── parser.py          # استخلاص الرسائل
│   ├── storage.py         # طبقة التخزين
│   ├── styles.py          # التنسيقات البصرية
│   └── util.py            # الأدوات المساعدة
├── tests/                 # الاختبارات
├── .streamlit/            # إعدادات Streamlit
│   ├── config.toml
│   └── secrets.toml.example
└── requirements.txt        # المكتبات المطلوبة
```

## الميزات

- ✅ إدارة دورات الزيت بشكل مستقل لكل سيارة
- ✅ تحليل آلي لرسائل السائقين
- ✅ تنبيهات ذكية عند اقتراب موعد الصيانة
- ✅ تقارير شهرية وتحليلات شاملة
- ✅ تجاوب كامل مع شاشات الجوال
- ✅ واجهة عربية كاملة (RTL)
- ✅ نظام تراجع (Undo) عن العمليات
- ✅ تخزين سحابي دائم في Google Sheets

## الإصدار

الإصدار الحالي: 1.0.0
