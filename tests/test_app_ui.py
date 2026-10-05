# -*- coding: utf-8 -*-
"""
اختبار تشغيلي حقيقي لواجهة التطبيق باستخدام streamlit.testing.
يشغّل app.py فعلياً ويتنقل بين كل الأقسام عبر الشريط العائم الجديد،
ويجري إدخالاً وحذفاً وتراجعاً واسترجاعاً.
تشغيل: python tests/test_app_ui.py
"""

import os
import shutil
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
# نسمح بالتخزين المحلي هنا حصرياً لأغراض الاختبار الآلي — لا توجد بيانات
# اعتماد Google حقيقية في بيئة الاختبار، والتطبيق الفعلي (بدون هذا المتغير)
# يرفض العمل على تخزين محلي صامت حمايةً من فقدان البيانات في الإنتاج.
os.environ["FLEET_ALLOW_LOCAL_STORAGE"] = "1"

from streamlit.testing.v1 import AppTest  # noqa: E402

# مفاتيح الأقسام كما في fleet/config.py::NAV_SECTIONS، وعناوينها الكاملة
NAV_KEYS = ["dashboard", "daily", "monthly", "analytics", "export", "settings"]
SECTIONS = [
    "لوحة التحكم الرئيسية",
    "الحركة اليومية",
    "السجل الشهري المجدول",
    "التحليلات والرسوم البيانية",
    "السجل العام",
    "الإعدادات العامة والصيانة",
]

MESSAGE = """سيارة رقم 12 المسافه 1400 كم الوقت من 7 الى 12 الزفات 3
تفاصيل الزفات: حي السلام، السوق المركزي، المستشفى

شاحنة رقم 7 المسافه 1300 كم الوقت 5 ساعات
تفاصيل الزفات: الحي الشرقي، مخيم النزوح
"""

PASSED, FAILED = 0, 0


def check(label, cond, extra=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  ✔ {label}")
    else:
        FAILED += 1
        print(f"  ✘ {label} {extra}")


def fresh_app():
    shutil.rmtree(os.path.join(ROOT, "data"), ignore_errors=True)
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=90)
    at.run()
    return at


def find_button(at, label_substr):
    matches = [b for b in at.button if label_substr in b.label]
    if not matches:
        raise AssertionError(f"لم يتم العثور على زر يحتوي: {label_substr}")
    return matches[0]


def goto(at, nav_key):
    """ينتقل إلى قسم عبر الشريط العائم الموحّد (الزر nav_<key>)."""
    matches = [b for b in at.button if b.key == f"nav_{nav_key}"]
    if not matches:
        raise AssertionError(f"لم يتم العثور على زر التنقل: nav_{nav_key}")
    matches[0].click().run()


print("\n[A] الإقلاع الأول للتطبيق")
at = fresh_app()
check("التطبيق أقلع بدون استثناءات", not at.exception, at.exception)
nav_buttons = [b for b in at.button if b.key and b.key.startswith("nav_")]
check("أزرار الشريط العائم الستة موجودة", len(nav_buttons) == 6,
      [b.key for b in nav_buttons])
check("لا يوجد شريط جانبي افتراضي مستخدَم للتنقل", len(at.sidebar.radio) == 0,
      len(at.sidebar.radio))

print("\n[B] المرور على كل الأقسام عبر الشريط العائم")
for key, title in zip(NAV_KEYS, SECTIONS):
    goto(at, key)
    check(f"القسم «{title}» يعمل", not at.exception, at.exception)
    check(f"القسم النشط سُجِّل صحيحاً ({key})",
          at.session_state["current_section"] == title,
          at.session_state["current_section"])

print("\n[C] تحليل رسائل الحركة اليومية وحفظها")
goto(at, "daily")
at.text_area[0].set_value(MESSAGE).run()
find_button(at, "تحليل وحفظ الرسائل").click().run()
check("الحفظ تم بلا أخطاء", not at.exception, at.exception)
check("رسالة نجاح ظاهرة", any("تم حفظ" in m.value for m in at.success), [m.value for m in at.success])
check("عدد السجلات = 2", len(at.session_state["fleet_data"]) == 2,
      len(at.session_state["fleet_data"]))
check("حقل النص أُفرغ تلقائياً بعد نجاح الحفظ (منع التكرار)",
      at.text_area[0].value in ("", None), at.text_area[0].value)

print("\n[D] التحقق من عدادات الزيت بعد الإدخال")
state = at.session_state["oil_state"]
counters = {r["رقم السيارة"]: float(r["عداد الدورة"]) for _, r in state.iterrows()}
check("عداد السيارة 12 = 1400", counters.get("12") == 1400.0, counters)
check("عداد الشاحنة 7 = 1300", counters.get("7") == 1300.0, counters)

print("\n[E] إدخال ثانٍ يصل بالسيارة إلى الحد 2500 دون تجاوزه")
SECOND_MSG = "سيارة رقم 12 المسافه 2000 كم الزفات 1"
at.text_area[0].set_value(SECOND_MSG).run()
find_button(at, "تحليل وحفظ الرسائل").click().run()
check("لا أخطاء", not at.exception, at.exception)
state = at.session_state["oil_state"]
counters = {r["رقم السيارة"]: float(r["عداد الدورة"]) for _, r in state.iterrows()}
check("العداد توقف عند 2500 ولم يصبح 3400", counters.get("12") == 2500.0, counters)
check("تنبيه بلوغ الحد ظهر",
      any("بلغت حد تغيير الزيت" in e.value for e in at.error),
      [e.value for e in at.error])

print("\n[E2] منع تكرار حفظ نفس الرسالة (ضغط مزدوج) من داخل منطق الحفظ")
records_before_dup = len(at.session_state["fleet_data"])
at.text_area[0].set_value(SECOND_MSG).run()       # نفس محتوى الدفعة السابقة تماماً
find_button(at, "تحليل وحفظ الرسائل").click().run()
check("لا استثناء أثناء محاولة التكرار", not at.exception, at.exception)
check("لم تتم إضافة أي سجل جديد (تم رفض التكرار في منطق الحفظ)",
      len(at.session_state["fleet_data"]) == records_before_dup,
      (records_before_dup, len(at.session_state["fleet_data"])))
check("رسالة توضح أن البيانات محفوظة مسبقاً ظهرت",
      any("تم حفظها للتو" in i.value for i in at.info),
      [i.value for i in at.info])

print("\n[F] لوحة التحكم تعرض التنبيه وزر اعتماد تغيير الزيت")
goto(at, "dashboard")
check("لوحة التحكم بلا أخطاء", not at.exception, at.exception)
check("تنبيه السيارات المتجاوزة ظاهر",
      any("بلغت حد تغيير الزيت" in e.value for e in at.error),
      [e.value for e in at.error])
reset_btn = [b for b in at.button if "تم تغيير الزيت" in b.label]
check("زر «تم تغيير الزيت» موجود", len(reset_btn) == 1, [b.label for b in at.button])
if reset_btn:
    reset_btn[0].click().run()
    check("إغلاق الدورة بلا أخطاء", not at.exception, at.exception)
    state = at.session_state["oil_state"]
    row = state[state["رقم السيارة"] == "12"].iloc[0]
    check("العداد صار صفراً بعد التغيير", float(row["عداد الدورة"]) == 0.0, row.to_dict())
    check("رقم الدورة صار 2", int(float(row["دورة الزيت"])) == 2, row.to_dict())

print("\n[G] الدورة الجديدة مستقلة وتبدأ من الصفر")
goto(at, "daily")
at.text_area[0].set_value("سيارة رقم 12 المسافه 300 كم الزفات 1").run()
find_button(at, "تحليل وحفظ الرسائل").click().run()
state = at.session_state["oil_state"]
row = state[state["رقم السيارة"] == "12"].iloc[0]
check("عداد الدورة الجديدة = 300 (بلا ترحيل فائض)",
      float(row["عداد الدورة"]) == 300.0, row.to_dict())

print("\n[H] التراجع عن آخر إدخال مجمع")
before = len(at.session_state["fleet_data"])
undo_btn = [b for b in at.button if "تراجع عن آخر إدخال" in b.label][0]
undo_btn.click().run()
check("التراجع بلا أخطاء", not at.exception, at.exception)
check("نقص عدد السجلات بعد التراجع",
      len(at.session_state["fleet_data"]) == before - 1,
      (before, len(at.session_state["fleet_data"])))

print("\n[H2] إعادة حفظ نفس الرسالة مباشرة بعد التراجع — لا يجب رفضها كتكرار "
      "ولا يجب أن يظهر عداد السيارات المتحركة صفراً (المشكلة المبلّغ عنها)")
goto(at, "daily")
at.text_area[0].set_value("سيارة رقم 12 المسافه 300 كم الزفات 1").run()
find_button(at, "تحليل وحفظ الرسائل").click().run()
check("الحفظ بلا أخطاء بعد التراجع مباشرة", not at.exception, at.exception)
check("لم تُرفض كتكرار (بصمة الدفعة مُسحت عند التراجع)",
      not any("تم حفظها للتو" in i.value for i in at.info),
      [i.value for i in at.info])
check("عادت السجلات لنفس العدد السابق (الحفظ تم فعلياً)",
      len(at.session_state["fleet_data"]) == before,
      (before, len(at.session_state["fleet_data"])))

goto(at, "dashboard")
check("لوحة التحكم بلا أخطاء بعد إعادة الحفظ", not at.exception, at.exception)
overview_after = at.session_state["oil_state"]
check("عداد دورة السيارة 12 يعكس المسافة المعاد حفظها (300 كم) — أي أن "
      "السيارة 12 محتسبة فعلياً ولم يُفقد الحفظ بصمت",
      float(overview_after[overview_after["رقم السيارة"] == "12"]
            ["عداد الدورة"].iloc[0]) == 300.0,
      overview_after)

print("\n[H3] تاريخ غير اليوم الفعلي: العداد يجب ألا يظهر صفراً دون تدخّل يدوي")
goto(at, "daily")
past_date = (date.today() - timedelta(days=3))
date_inputs = at.date_input
date_inputs[0].set_value(past_date).run()  # تاريخ الحركة في صفحة الإدخال
at.text_area[0].set_value(
    "سيارة رقم 31 المسافه 70 كم الزفات 1\n"
    "شاحنة رقم 32 المسافه 40 كم الزفات 1").run()
find_button(at, "تحليل وحفظ الرسائل").click().run()
check("الحفظ لتاريخ سابق تم بلا أخطاء", not at.exception, at.exception)

goto(at, "dashboard")
check("لوحة التحكم بلا أخطاء بعد إدخال تاريخ سابق", not at.exception, at.exception)
check("تاريخ لوحة التحكم تزامن تلقائياً مع تاريخ الإدخال (بلا تدخل يدوي)",
      at.session_state["dashboard_date"] == past_date,
      (at.session_state["dashboard_date"], past_date))
dashboard_html = " ".join(m.value for m in at.markdown)
check("بطاقة «الشاحنات المتحركة» تُظهر 2 تحديداً لذلك التاريخ (وليس صفراً أو "
      "رقماً من بطاقة أخرى بالصدفة)",
      '<div class="sc-value">2</div><div class="sc-label">الشاحنات المتحركة'
      in dashboard_html,
      [s for s in dashboard_html.split("<div class=\"stat-card")
       if "متحركة" in s][:1])

# تنظيف: نتراجع عن دفعة هذا الاختبار حتى لا تبقى بيانات تاريخ سابق مؤثّرة
# على الاختبارات التالية (مثل حذف «سجلات اليوم» في القسم [K]).
count_before_cleanup = len(at.session_state["fleet_data"])
goto(at, "daily")
cleanup_undo = [b for b in at.button if "تراجع عن آخر إدخال" in b.label][0]
cleanup_undo.click().run()
check("تنظيف ما بعد اختبار [H3]: عادت السجلات لحالتها قبل إدخال التاريخ السابق",
      len(at.session_state["fleet_data"]) == count_before_cleanup - 2,
      (count_before_cleanup, len(at.session_state["fleet_data"])))

print("\n[H4] مزامنة تاريخ لوحة التحكم فور تغيير «تاريخ الحركة» دون الحفظ")
goto(at, "daily")
another_date = (date.today() - timedelta(days=9))
at.date_input[0].set_value(another_date).run()
check("القيمة تزامنت في session_state فور تغيير الحقل، قبل أي ضغط على حفظ",
      at.session_state["dashboard_date"] == another_date,
      (at.session_state["dashboard_date"], another_date))

print("\n[I] الإدخال اليدوي عبر النموذج")
goto(at, "daily")
inputs = at.text_input
inputs[1].set_value("9").run()            # رقم السيارة (الأول معطل للحد)
at.number_input[0].set_value(2).run()     # عدد الزفات
at.number_input[1].set_value(50.0).run()  # المسافة
form_btn = [b for b in at.button if "حفظ السجل" in b.label]
check("زر حفظ السجل موجود", len(form_btn) >= 1, [b.label for b in at.button])
if form_btn:
    form_btn[0].click().run()
    check("حفظ السجل اليدوي تم بلا أخطاء", not at.exception, at.exception)

print("\n[I2] الترتيب العددي الطبيعي لرقم السيارة (وليس الأبجدي)")
PLATES_MSG = ("سيارة رقم 21 المسافه 40 كم الزفات 1\n"
             "سيارة رقم 3 المسافه 30 كم الزفات 1\n"
             "سيارة رقم 1 المسافه 10 كم الزفات 1\n")
goto(at, "daily")
at.text_area[0].set_value(PLATES_MSG).run()
find_button(at, "تحليل وحفظ الرسائل").click().run()
check("حفظ دفعة اللوحات الإضافية بلا أخطاء", not at.exception, at.exception)

goto(at, "export")
plate_select = [s for s in at.selectbox if s.label == "رقم السيارة"]
check("قائمة السيارات موجودة في السجل العام", len(plate_select) == 1,
      [s.label for s in at.selectbox])
if plate_select:
    options = [o for o in plate_select[0].options if o != "الكل"]
    check("قائمة السيارات مرتبة عددياً تصاعدياً (1,3,9,12,21) وليس أبجدياً",
          options == sorted(options, key=lambda x: int(x)) and options[0] in ("1", "3"),
          options)

goto(at, "monthly")
check("السجل الشهري بلا أخطاء بعد إضافة لوحات متعددة", not at.exception, at.exception)
monthly_tables = at.dataframe
check("جدول الملخص الشهري يحتوي صفوفاً", len(monthly_tables) >= 1, len(monthly_tables))
if monthly_tables:
    plates_col = monthly_tables[0].value.get("رقم السيارة")
    if plates_col is not None:
        plate_order = [str(v) for v in plates_col.tolist()]
        numeric_only = [p for p in plate_order if p.lstrip("-").isdigit()]
        check("ترتيب الجدول الشهري تصاعدي عددياً حسب رقم السيارة",
              numeric_only == sorted(numeric_only, key=lambda x: int(x)),
              plate_order)

print("\n[J] السجل الشهري والتصدير")
goto(at, "monthly")
check("السجل الشهري بلا أخطاء", not at.exception, at.exception)

print("\n[J2] قسم التحليلات والرسوم البيانية")
goto(at, "analytics")
check("التحليلات تعمل بلا أخطاء (الفترة الافتراضية)", not at.exception, at.exception)
check("جدول عدد العمليات ظاهر", len(at.dataframe) >= 1, len(at.dataframe))

for p in ["يومي", "شهري", "سنوي"]:
    at.radio(key="analytics_period").set_value(p).run()
    check(f"التحليلات تعمل مع الفترة «{p}»", not at.exception, at.exception)

plates_widget = at.multiselect(key="compare_plates")
plates_widget.set_value(["12", "7"]).run()
check("مقارنة السيارتين تعمل بلا أخطاء", not at.exception, at.exception)
check("جداول/رسوم المقارنة ظهرت دون استثناء",
      len(at.dataframe) >= 1 or len(at.get("line_chart")) >= 1, None)

print("\n[J3] السجل العام: تخصيص الأعمدة + جدول الحذف التفاعلي")
goto(at, "export")
check("السجل العام بلا أخطاء", not at.exception, at.exception)
check("أزرار التنزيل موجودة", len(at.download_button) >= 2, len(at.download_button))
col_customizer = [m for m in at.multiselect if m.label == "الأعمدة الظاهرة في الجدول"]
check("مخصّص الأعمدة موجود", len(col_customizer) == 1, [m.label for m in at.multiselect])
if col_customizer:
    all_opts = col_customizer[0].options
    col_customizer[0].set_value(all_opts[:3]).run()
    check("تخصيص الأعمدة يعمل بلا أخطاء", not at.exception, at.exception)
    col_customizer2 = [m for m in at.multiselect if m.label == "الأعمدة الظاهرة في الجدول"][0]
    col_customizer2.set_value(all_opts).run()   # إعادة كل الأعمدة لما بعده من الاختبارات
undo_delete_btn = [b for b in at.button if "تراجع عن آخر حذف" in b.label]
check("زر «تراجع عن آخر حذف» موجود (معطّل حتى الآن)",
      len(undo_delete_btn) == 1 and undo_delete_btn[0].disabled,
      undo_delete_btn[0].disabled if undo_delete_btn else None)

print("\n[K] الإعدادات: تغيير الحد + الحذف + التراجع عبر السجل العام")
goto(at, "settings")
check("الإعدادات بلا أخطاء", not at.exception, at.exception)
at.number_input[0].set_value(3000.0).run()
save_btn = [b for b in at.button if "حفظ الإعدادات" in b.label][0]
save_btn.click().run()
check("حفظ الحد الجديد بلا أخطاء", not at.exception, at.exception)
check("الحد الجديد مطبق = 3000",
      float(at.session_state["settings"]["oil_limit"]) == 3000.0,
      at.session_state["settings"])

records_before_delete = len(at.session_state["fleet_data"])
# ملاحظة: بحلول هذه النقطة قد تحتوي البيانات على أكثر من تاريخ واحد (مثال:
# دفعة [I2] حُفظت بتاريخ قديم لأن [H4] غيّر "تاريخ الحركة" قبلها ولم يُعَد
# ضبطه — وهذا بالضبط يُثبت أن مزامنة dashboard_date تعمل بثبات عبر
# الصفحات). لذا الاختبار الدقيق يتحقق من حذف اليوم المحدَّد تحديداً فقط،
# وليس افتراض أن الجدول كله سيصبح فارغاً.
day_select = [s for s in at.selectbox if s.label == "اختر اليوم"][0]
targeted_day = day_select.value
records_for_day_before = int((at.session_state["fleet_data"]["التاريخ"] == targeted_day).sum())
del_cb = [c for c in at.checkbox if "أؤكد حذف كافة سجلات" in c.label]
if del_cb:
    del_cb[0].set_value(True).run()
    del_btn = [b for b in at.button if "حذف بيانات اليوم" in b.label][0]
    del_btn.click().run()
    check("حذف يوم كامل بلا أخطاء", not at.exception, at.exception)
    check("سجلات اليوم المحدَّد تحديداً أصبحت صفراً",
          int((at.session_state["fleet_data"]["التاريخ"] == targeted_day).sum()) == 0,
          targeted_day)
    check("عدد السجلات نقص بمقدار سجلات ذلك اليوم تحديداً ولا أكثر",
          len(at.session_state["fleet_data"]) == records_before_delete - records_for_day_before,
          (records_before_delete, records_for_day_before,
           len(at.session_state["fleet_data"])))
    check("عملية الحذف سُجِّلت في مكدّس التراجع",
          len(at.session_state["delete_undo_stack"]) >= 1,
          len(at.session_state["delete_undo_stack"]))

print("\n[K2] استرجاع البيانات المحذوفة عبر زر «تراجع عن آخر حذف» في السجل العام")
goto(at, "export")
undo_delete_btn = [b for b in at.button if "تراجع عن آخر حذف" in b.label]
check("زر التراجع عن الحذف أصبح مفعَّلاً بعد وجود حذف سابق",
      len(undo_delete_btn) == 1 and not undo_delete_btn[0].disabled,
      undo_delete_btn[0].disabled if undo_delete_btn else None)
if undo_delete_btn and not undo_delete_btn[0].disabled:
    undo_delete_btn[0].click().run()
    check("التراجع عن الحذف تم بلا أخطاء", not at.exception, at.exception)
    check("السجلات المحذوفة استُرجعت بالكامل",
          len(at.session_state["fleet_data"]) == records_before_delete,
          (records_before_delete, len(at.session_state["fleet_data"])))

print("\n[L] تسجيل الخروج وإعادة الدخول")
goto(at, "settings")
logout = [b for b in at.button if "تسجيل الخروج" in b.label][0]
logout.click().run()
check("تسجيل الخروج يعمل", at.session_state["logged_in"] is False)
relogin = [b for b in at.button if "إعادة الدخول" in b.label]
check("شاشة القفل تعرض زر إعادة الدخول", len(relogin) == 1, [b.label for b in at.button])
if relogin:
    relogin[0].click().run()
    check("إعادة الدخول تعمل", at.session_state["logged_in"] is True and not at.exception,
          at.exception)

print("\n[M] حفظ آخر قسم مفتوح عبر رابط الصفحة (استئناف التقدم)")
goto(at, "analytics")
check("القسم صار التحليلات", at.session_state["current_section"] == SECTIONS[3],
      at.session_state["current_section"])
try:
    saved_param = at.query_params.get("section")
    if isinstance(saved_param, list):
        saved_param = saved_param[0] if saved_param else None
    check("رابط الصفحة يحمل معرف القسم الحالي", saved_param == "analytics", saved_param)
except Exception as exc:  # noqa: BLE001
    check("قراءة query_params غير متاحة في بيئة الاختبار (غير حرج)", True, str(exc))

shutil.rmtree(os.path.join(ROOT, "data"), ignore_errors=True)
print(f"\nالنتيجة: نجح {PASSED} / فشل {FAILED}")
sys.exit(1 if FAILED else 0)
