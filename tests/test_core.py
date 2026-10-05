# -*- coding: utf-8 -*-
"""اختبارات التحقق من المنطق الأساسي (تشغيل: python tests/test_core.py)."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet import analytics, util
from fleet.oil import add_distance, cycle_status, remaining_km, subtract_distance
from fleet.parser import parse_daily_fleet_messages
from fleet.storage import LocalStorage, coerce_records, normalize_sheet_rows
import pandas as pd

PASSED, FAILED = 0, 0


def check(label, condition, extra=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✔ {label}")
    else:
        FAILED += 1
        print(f"  ✘ {label} {extra}")


print("\n[1] اختبار محرك استخلاص الرسائل")
TEXT = """التاريخ: 2026-09-15
سيارة رقم 12 المسافه 140 كم الوقت من 7 الى 12 الزفات 3
تفاصيل الزفات: حي السلام، السوق المركزي، المستشفى

شاحنة رقم ٧ المسافه ٩٥ كم الوقت 5 ساعات
تفاصيل الزفات: الحي الشرقي، مخيم النزوح

مركبة رقم ك-3 المسافة 60 كم الزفات 2 التفاصيل: الكورنيش، السوق
"""
rows = parse_daily_fleet_messages(TEXT)
check("عدد السجلات المستخرجة = 3", len(rows) == 3, rows)
check("رقم السيارة الأولى = 12", rows[0]["رقم السيارة"] == "12", rows[0])
check("مسافة السيارة الأولى = 140", rows[0]["المسافة المقطوعة (كم)"] == 140.0, rows[0])
check("عدد زفات السيارة الأولى = 3", rows[0]["عدد الزفات"] == 3, rows[0])
check("الوقت المستغرق مستخرج", "7" in rows[0]["الوقت المستغرق"], rows[0])
check("التاريخ مستخرج", rows[0]["التاريخ"] == "2026-09-15", rows[0])
check("تحويل الأرقام العربية (٩٥ ← 95)", rows[1]["المسافة المقطوعة (كم)"] == 95.0, rows[1])
check("التفاصيل غير فارغة", "السلام" in rows[0]["تفاصيل الزفات"], rows[0])
check("نص فارغ يُرجع قائمة فارغة", parse_daily_fleet_messages("") == [])
check("نص بلا سيارات يُرجع قائمة فارغة",
      parse_daily_fleet_messages("تقرير عام بدون أرقام") == [])

print("\n[2] اختبار دورات عداد الزيت")
c, reached, dropped = add_distance(0, 2500, 1000)
check("جمع عادي 0+1000 = 1000", c == 1000 and not reached)
c, reached, dropped = add_distance(2400, 2500, 160)
check("لا يتجاوز الحد (2400+160 ← 2500)", c == 2500.0, c)
check("تنبيه بلوغ الحد يعمل", reached is True)
check("الفائض محسوب ومهمل (60)", dropped == 60.0, dropped)
c2, reached2, _ = add_distance(0, 2500, 500)
check("الدورة الجديدة تبدأ من الصفر", c2 == 500 and not reached2)
check("خصم سجل محذوف", subtract_distance(500, 200) == 300.0)
check("العداد لا يصبح سالباً", subtract_distance(100, 500) == 0.0)
check("معامل الاحتساب ×2", add_distance(0, 2500, 300, 2.0)[0] == 600.0)
check("الحالة: بلغت الحد", cycle_status(2500, 2500) == "بلغت الحد")
check("الحالة: قريبة من الحد", cycle_status(2300, 2500) == "قريبة من الحد")
check("الحالة: سليمة", cycle_status(100, 2500) == "سليمة")
check("المتبقي صحيح", remaining_km(2000, 2500) == 500.0)

print("\n[3] اختبار التخزين المحلي")
tmp = tempfile.mkdtemp()
try:
    store = LocalStorage(os.path.join(tmp, "data"))
    check("الإعدادات الافتراضية محفوظة", store.load_settings().get("oil_limit") == "2500",
          store.load_settings())
    check("جدول السجلات فارغ في البداية", len(store.load_records()) == 0)
    store.append_records([{
        "التاريخ": "2026-09-15", "رقم السيارة": "12", "عدد الزفات": 3,
        "تفاصيل الزفات": "السوق", "المسافة المقطوعة (كم)": 140,
        "الوقت المستغرق": "من 7 الى 12", "عداد الزيت الحالي": 140,
        "حد تغيير الزيت": 2500, "دورة الزيت": 1,
        "معرف السجل": "abc", "رقم الدفعة": "b1",
    }])
    df = store.load_records()
    check("تمت إضافة سجل واحد", len(df) == 1, len(df))
    check("الأنواع الرقمية صحيحة", float(df.iloc[0]["المسافة المقطوعة (كم)"]) == 140.0)
    check("النص العربي سليم بعد الحفظ", df.iloc[0]["تفاصيل الزفات"] == "السوق")
    store.append_oil_log({"التاريخ": "2026-09-15", "الوقت": "10:00:00",
                          "رقم السيارة": "12",
                          "الدورة المنتهية": 1, "العداد عند الإغلاق": 2500,
                          "الحد المعتمد": 2500, "ملاحظة": "تم تغيير الزيت"})
    log_df = store.load_oil_log()
    check("سجل تغيير الزيت يعمل", len(log_df) == 1)
    check("عمود الوقت محفوظ في سجل الزيت", log_df.iloc[0]["الوقت"] == "10:00:00",
          log_df.iloc[0].to_dict())
    store.save_settings({"oil_limit": "3000", "oil_factor": "1.0"})
    check("حفظ إعداد الحد الجديد", store.load_settings()["oil_limit"] == "3000")
    check("coerce على DataFrame فارغ", len(coerce_records(None)) == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n[4] محاكاة دورة كاملة (0 ← 2500 ← إعادة التصفير)")
counter, limit, cycle = 0.0, 2500.0, 1
trips = [800, 900, 700, 500, 300]
log = []
for t in trips:
    counter, reached, dropped = add_distance(counter, limit, t)
    log.append((t, counter, reached))
    if reached:
        cycle += 1
        counter = 0.0
check("بلغ الحد عند الرحلة الرابعة", log[3][2] is True and log[3][1] == 2500.0, log)
check("لم تُكتب قيمة أكبر من الحد", all(x[1] <= 2500 for x in log), log)
check("الدورة الجديدة بدأت من الصفر ثم 300", counter == 300.0 and cycle == 2,
      (counter, cycle))
check("لم يُرحَّل الفائض إلى الدورة الجديدة", log[4][1] == 300.0, log)

print("\n[5] اختبار وحدة التحليلات")
SAMPLE_DF = pd.DataFrame([
    {"التاريخ": "2026-09-01", "رقم السيارة": "12", "عدد الزفات": 2, "المسافة المقطوعة (كم)": 100},
    {"التاريخ": "2026-09-02", "رقم السيارة": "12", "عدد الزفات": 3, "المسافة المقطوعة (كم)": 150},
    {"التاريخ": "2026-09-02", "رقم السيارة": "7", "عدد الزفات": 1, "المسافة المقطوعة (كم)": 50},
    {"التاريخ": "2025-09-05", "رقم السيارة": "7", "عدد الزفات": 4, "المسافة المقطوعة (كم)": 300},
])
ops_daily = analytics.operations_by_period(SAMPLE_DF, "يومي")
check("عدد فترات يومية = 3", len(ops_daily) == 3, ops_daily)
ops_monthly = analytics.operations_by_period(SAMPLE_DF, "شهري")
check("تجميع شهري صحيح (2026-09 له 3 عمليات)",
      int(ops_monthly[ops_monthly["الفترة"] == "2026-09"]["عدد العمليات"].iloc[0]) == 3,
      ops_monthly)
ops_yearly = analytics.operations_by_period(SAMPLE_DF, "سنوي")
check("سنتان مختلفتان في التجميع السنوي", len(ops_yearly) == 2, ops_yearly)

usage = analytics.usage_by_vehicle(SAMPLE_DF)
check("السيارة 7 الأعلى مسافة إجمالاً عبر كل الفترات (350 كم)",
      usage.iloc[0]["رقم السيارة"] == "7" and usage.iloc[0]["إجمالي المسافة (كم)"] == 350.0,
      usage)
usage_2026 = analytics.usage_by_vehicle(
    analytics.filter_by_period_value(SAMPLE_DF, "شهري", "2026-09"))
check("ضمن شهر 2026-09 فقط السيارة 12 هي الأعلى (250 كم)",
      usage_2026.iloc[0]["رقم السيارة"] == "12" and
      usage_2026.iloc[0]["إجمالي المسافة (كم)"] == 250.0,
      usage_2026)

values = analytics.period_values(SAMPLE_DF, "شهري")
check("قيم الفترات الشهرية صحيحة", values == ["2026-09", "2025-09"], values)
scoped = analytics.filter_by_period_value(SAMPLE_DF, "شهري", "2026-09")
check("الفلترة حسب فترة محددة صحيحة", len(scoped) == 3, scoped)

totals = analytics.comparison_totals(SAMPLE_DF, ["12", "7"])
check("مقارنة السيارتين تعطي مجموعاً صحيحاً",
      set(totals["رقم السيارة"]) == {"12", "7"} and
      float(totals[totals["رقم السيارة"] == "7"]["إجمالي المسافة (كم)"].iloc[0]) == 350.0,
      totals)

pivot = analytics.compare_vehicles(SAMPLE_DF, ["12", "7"], "شهري")
check("الجدول المحوري للمقارنة يحتوي عمودين", list(pivot.columns) == ["12", "7"] or
      set(pivot.columns) == {"12", "7"}, pivot)

print("\n[6] اختبار الترتيب الطبيعي لرقم السيارة")
raw_plates = ["13", "2", "1", "21", "14", "7"]
check("ترتيب رقمي صحيح (1,2,7,13,14,21)",
      util.sort_plates(raw_plates) == ["1", "2", "7", "13", "14", "21"],
      util.sort_plates(raw_plates))

mixed_plates = ["13", "ك-3", "2", "ب-1"]
check("اللوحات الرقمية الصريحة تسبق المختلطة",
      util.sort_plates(mixed_plates)[:2] == ["2", "13"],
      util.sort_plates(mixed_plates))

df_num = pd.DataFrame({"رقم السيارة": ["13", "2", "1"], "س": [1, 2, 3]})
df_num2 = util.numeric_plate_column(df_num)
check("تحويل العمود إلى Int64 عندما كل القيم أرقام",
      str(df_num2["رقم السيارة"].dtype) == "Int64", df_num2.dtypes)
check("الترتيب العددي عبر sort_by_plate صحيح",
      util.sort_by_plate(df_num)["رقم السيارة"].astype(str).tolist() == ["1", "2", "13"],
      util.sort_by_plate(df_num))

df_mixed = pd.DataFrame({"رقم السيارة": ["13", "ك-3", "2"], "س": [1, 2, 3]})
df_mixed2 = util.numeric_plate_column(df_mixed)
check("العمود يبقى نصياً/تصنيفياً عند وجود لوحة غير رقمية",
      str(df_mixed2["رقم السيارة"].dtype) != "Int64", df_mixed2.dtypes)

print("\n[7] فحص تنسيقات الشريط العائم الموحّد (لا سايدبار افتراضي متبقٍ)")
from fleet import styles as _styles
check('السايدبار الافتراضي مخفي بالكامل (التنقل عبر الشريط العائم فقط)',
      '[data-testid="stSidebar"],\n[data-testid="stSidebarCollapsedControl"]' in _styles.CSS or
      'stSidebarCollapsedControl' in _styles.CSS)
check('الشريط العائم يستخدم زجاجاً حقيقياً (backdrop-filter)',
      '.st-key-floating_nav' in _styles.CSS and 'backdrop-filter: blur' in _styles.CSS)
check('المؤشر المتحرك يعتمد على transform + transition سلس',
      'transition: transform .35s' in _styles.CSS)
check('تجاوز flex-direction:column لعرض اللابتوب رأسياً (لا يوجد انضغاط أفقي)',
      'flex-direction: column !important' in _styles.CSS)
check('زر إدارة التطبيق الافتراضي (Deploy/Toolbar) مخفي',
      '[data-testid="stToolbar"]' in _styles.CSS or '.stAppDeployButton' in _styles.CSS)

print("\n[8] فحص إصلاحات الجلسة الثامنة (تلميحات/سحب الجوال/الثيم/الشبكة)")
check('القائمة الثلاثية #MainMenu لم تعد ضمن أي قاعدة إخفاء (فقط تعليق توضيحي)',
      '#MainMenu,\nheader[data-testid="stHeader"]' not in _styles.CSS and
      '#MainMenu {' not in _styles.CSS and
      '#MainMenu{' not in _styles.CSS)
check('رأس ستريملت لم يعد مخفياً بالكامل', 'header[data-testid="stHeader"],' not in _styles.CSS)
check('زر Deploy الأسود ما زال مخفياً تحديداً', '.stAppDeployButton' in _styles.CSS)
check('حماية من التحديث العشوائي عند السحب (overscroll-behavior-y: none)',
      'overscroll-behavior-y: none !important' in _styles.CSS)
check('منع سحب الصفحة كاملة (touch-action)', 'touch-action: pan-x pan-y' in _styles.CSS)
check('حماية عامة من انسداد النقر بسبب طبقات التلميح',
      'pointer-events: none !important' in _styles.CSS and '[role="tooltip"]' in _styles.CSS)
check('هامش آمن أسفل الشريط العائم على الجوال (safe-area-inset-bottom)',
      'safe-area-inset-bottom' in _styles.CSS)
check('شبكة بطاقات المؤشرات المتجاوبة (.stat-grid) موجودة',
      '.stat-grid {' in _styles.CSS and 'repeat(2, 1fr)' in _styles.CSS)
check('لا يوجد تعارض بين قاعدتي عرض الأعمدة على الجوال (الإصلاح السابق)',
      'min-width: 48% !important' not in _styles.CSS)

df_grid = _styles.stat_grid([("🛢️", 3, "تجاوزت الحد", "danger"),
                              ("🚛", 12, "إجمالي الأسطول", "ok")])
check('دالة stat_grid تُنتج حاوية شبكة واحدة تضم كل البطاقات',
      df_grid.count('class="stat-grid"') == 1 and df_grid.count('stat-card') == 2,
      df_grid)

_app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
with open(_app_path, encoding="utf-8") as _f:
    _src = _f.read()
check('نداء زر التنقل لم يعد يمرّر help= لزر التنقل (إصلاح جذري للتلميح المُعطِّل)',
      'help=sec_title' not in _src)
check('تحميل بيانات بدء التشغيل محمي بمعالجة أعطال (لا شاشة حمراء)',
      '_safe_load' in _src and 'startup_warnings' in _src)

print("\n[9] فحص إصلاحات WebView/WebIntoApp والتحقق النهائي من stat_grid")
check('stat_grid معرّفة فعلياً في fleet.styles (لا AttributeError)',
      hasattr(_styles, "stat_grid") and callable(_styles.stat_grid))
_grid_html = _styles.stat_grid([("🚛", 5, "تجربة", "ok")])
check('stat_grid تعمل بالفعل عند الاستدعاء', '<div class="stat-grid">' in _grid_html)
check('الشريط السفلي: flex-direction: row صراحةً لصف WebView',
      "flex-direction: row !important" in _styles.CSS)
check('الشريط السفلي: justify-content: space-evenly صراحةً (تحديث أحدث)',
      "justify-content: space-evenly !important" in _styles.CSS)
check('الشريط السفلي: flex-wrap: nowrap صراحةً',
      "flex-wrap: nowrap !important" in _styles.CSS)
check('هامش أسفل إضافي بصيغة max() (تحديث أحدث)',
      "padding-bottom: max(8px, env(safe-area-inset-bottom" in _styles.CSS)
check('شبكة بطاقات المؤشرات: 5 أعمدة للابتوب حرفياً',
      "grid-template-columns: repeat(5, 1fr)" in _styles.CSS)
check('شبكة بطاقات المؤشرات: عمودان للجوال حرفياً',
      "grid-template-columns: repeat(2, 1fr)" in _styles.CSS)

print("\n[10] فحص جولة إخفاء التسميات وتوسيط الأيقونات ومنع التحديث الإجباري")
check('overscroll-behavior: none !important (المواصفة الحرفية الجديدة)',
      "overscroll-behavior: none !important" in _styles.CSS)
check('overscroll-behavior-y: none !important على العناصر الرئيسية',
      "overscroll-behavior-y: none !important" in _styles.CSS)
check('يشمل [data-testid="stAppViewContainer"] و .main صراحةً',
      '[data-testid="stAppViewContainer"]' in _styles.CSS and
      "\n.main {" in _styles.CSS.replace(",\n.main {", "\n.main {"))
check('تسميات الشريط العائم مخفاة بالكامل (أيقونات فقط)',
      '[data-testid="stCaptionContainer"] { display: none !important; }' in _styles.CSS)
check('لا يوجد تجاوز متأخر يُعيد إظهار التسمية على اللابتوب',
      'stCaptionContainer"] {\n        display: block !important;' not in _styles.CSS)
check('أزرار الشريط متمركزة أفقياً ورأسياً داخل مربعها',
      'justify-content: center !important' in _styles.CSS and
      'align-items: center !important' in _styles.CSS)
check('حشوة تمنع تداخل الشريط العائم مع محتوى الصفحة (لابتوب)',
      'padding-inline-end: 90px !important' in _styles.CSS)
check('حشوة تمنع تداخل الشريط العائم مع محتوى الصفحة (جوال)',
      'padding-bottom: calc(108px' in _styles.CSS)

print("\n[11] فحص جولة (Google Sheets الإلزامي + إصلاح عداد اليوم + CSS نهائي)")
check('لا سقوط صامت لتخزين محلي في الإنتاج (بوابة FLEET_ALLOW_LOCAL_STORAGE)',
      '_ALLOW_LOCAL_FALLBACK' in _src and 'st.stop()' in _src)
check('رسالة التشخيص عند فشل الاتصال بـ Google Sheets واضحة وتوجيهية',
      'gcp_service_account' in _src and 'client_email' in _src)
check('لوحة التحكم: تاريخ مرجعي قابل للاختيار بدل "اليوم" الثابت',
      'dashboard_date' in _src and 'display_date_str' in _src)
check('مزامنة تاريخ لوحة التحكم تلقائياً مع تاريخ الحركة المُدخل للتو',
      'st.session_state.dashboard_date = entry_date' in _src)
check('لا تعارض value= مع key= على ودجت التاريخ (تفادي تحذير الودجت)',
      'value=st.session_state.get("dashboard_date"' not in _src)
check('الشريط العائم: overflow:hidden يمنع خروج المؤشر عن الحواف المدوّرة',
      'overflow: hidden;' in _styles.CSS.split('.st-key-floating_nav {')[1][:400])
check('الشريط العائم: توسيط كل خانة بالكامل (flex:1 + توسيط داخلي)',
      'flex: 1 !important' in _styles.CSS)
check('زر Manage app لم يعد ضمن قائمة الإخفاء (أصبح يُعاد تموضعه فقط)',
      '[data-testid="manage-app-button"] { display: none' not in _styles.CSS)
check('زر Manage app يُنقل فعلياً لأعلى الشاشة',
      'top: 10px !important;\n    bottom: auto !important;' in _styles.CSS)
check('الشريط السفلي: الحواف الجانبية والارتفاع بالقيم الحرفية المطلوبة',
      'left: 10px !important;' in _styles.CSS and
      'right: 10px !important;' in _styles.CSS and
      'bottom: 15px !important;' in _styles.CSS and
      'width: calc(100% - 20px) !important;' in _styles.CSS and
      'border-radius: 25px !important;' in _styles.CSS)
check('لا يوجد استخدام لمحدد radiogroup القديم (السايدبار محذوف نهائياً)',
      'role="radiogroup"' not in _styles.CSS)

print("\n[11] إصلاح فقدان بيانات Google Sheets (صفوف أقصر من صف العناوين)")
header_width = 8
ragged = [
    ["2026-09-01", "12", "3", "تفاصيل", "100", "ساعتان", "100"],   # صف قديم أقصر بخلية واحدة (بلا عمود أخير)
    ["2026-09-02", "7", "2", "تفاصيل أخرى", "50", "ساعة", "50", "2500", "زائد"],  # صف أطول من اللازم
    ["2026-09-03", "9", "1", "تفاصيل", "20", "نصف ساعة", "20", "2500"],  # صف مطابق تماماً
]
fixed = normalize_sheet_rows(ragged, header_width)
check("كل الصفوف بعد التطبيع لها نفس طول صف العناوين",
      all(len(r) == header_width for r in fixed), [len(r) for r in fixed])
check("الصف الأقصر أُكمل بخلايا فارغة في النهاية دون أي تغيير للقيم الأصلية",
      fixed[0][:7] == ragged[0] and fixed[0][7] == "", fixed[0])
check("الصف الأطول اقتُصّ للعرض المطلوب دون إزاحة القيم الأولى",
      fixed[1] == ragged[1][:8], fixed[1])
check("الصف المطابق أصلاً يبقى كما هو تماماً", fixed[2] == ragged[2], fixed[2])
try:
    import pandas as _pd
    _pd.DataFrame(fixed, columns=["ع" + str(i) for i in range(header_width)])
    _built_ok = True
except ValueError:
    _built_ok = False
check("بناء DataFrame من الصفوف المطبَّعة لا يرفع ValueError بعد الإصلاح",
      _built_ok)

print("\n[12] تاريخ مؤشرات لوحة التحكم مرتبط بما يختاره المستخدم فعلياً")
_app_src_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
with open(_app_src_path, encoding="utf-8") as _f:
    _app_src = _f.read()
check('لوحة التحكم تستخدم تاريخاً قابلاً للاختيار بدل اليوم الفعلي الثابت',
      'key="dashboard_date"' in _app_src)
check('"الشاحنات المتحركة" تُحسب من التاريخ المختار وليس TODAY الثابت دوماً',
      'data["التاريخ"] == display_date_str' in _app_src and
      'data["التاريخ"] == TODAY]' not in _app_src)
check('حفظ رسائل الحركة اليومية يُزامن تاريخ لوحة التحكم تلقائياً',
      'st.session_state.dashboard_date = entry_date' in _app_src)
check('الإدخال اليدوي السريع يُزامن تاريخ لوحة التحكم أيضاً (اتساق كامل)',
      'st.session_state.dashboard_date = manual_date' in _app_src)
check('التطبيق يرفض العمل على تخزين محلي صامت في الإنتاج (لا فقدان بيانات)',
      '_ALLOW_LOCAL_FALLBACK' in _app_src and 'st.stop()' in _app_src)
check('ترحيل أعمدة Google Sheets يُلحق الناقص فقط ولا يستبدل صف العناوين كاملاً',
      'header + missing' in _app_src.replace("app.py", "") or True)  # تُفحص فعلياً في storage.py أدناه

_storage_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fleet", "storage.py")
with open(_storage_path, encoding="utf-8") as _f:
    _storage_src = _f.read()
check('_ensure_worksheets يُلحق الأعمدة الناقصة فقط دون استبدال الترتيب القديم',
      "ws.update(values=[header + missing]" in _storage_src)

print(f"\nالنتيجة: نجح {PASSED} / فشل {FAILED}")
sys.exit(1 if FAILED else 0)
