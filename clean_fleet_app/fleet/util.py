# -*- coding: utf-8 -*-
"""
أدوات مساعدة لعمود "رقم السيارة".

أغلب أرقام السيارات في النظام أرقام صحيحة بحتة (١٢، ٧، ٢١ ...)، لكن الراصد
(parser) يسمح أيضاً بلوحات مختلطة مثل "ك-3". لذلك:

  * `plate_sort_key`  يُرتّب الأرقام الصريحة عددياً (1, 2, 13, 14 ...) قبل أي
    لوحات مختلطة، ثم يرتّب المختلط بأقرب رقم ضمنه، ثم أبجدياً كحل أخير —
    بدل الترتيب النصي الافتراضي الذي كان يضع "13" قبل "2".
  * `sort_plates`      يُرجع قائمة مرتبة طبيعياً جاهزة للقوائم المنسدلة.
  * `numeric_plate_column` يحوّل عمود "رقم السيارة" في DataFrame إلى نوع
    عددي صحيح (Int64) عندما تكون كل القيم أرقاماً صريحة — وهو الحال الغالب —
    بحيث يُرتَّب العمود عددياً تلقائياً حتى عند النقر على رأس العمود في
    الجدول التفاعلي، لا نصياً. إن وُجدت لوحة غير رقمية يبقى العمود نصياً
    لكن بترتيب طبيعي (Categorical مرتّب) بدل الترتيب الأبجدي الافتراضي.
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

_LEADING_NUMBER = re.compile(r"-?\d+")


def plate_sort_key(value) -> tuple:
    """مفتاح ترتيب طبيعي: أرقام صريحة أولاً وبقيمتها العددية، ثم لوحات
    مختلطة برقمها الأول، ثم أي نص آخر أبجدياً."""
    s = str(value).strip()
    if s.lstrip("-").isdigit():
        return (0, int(s), "")
    m = _LEADING_NUMBER.search(s)
    if m:
        return (1, int(m.group()), s)
    return (2, 0, s)


def sort_plates(values) -> list:
    """يُرجع قائمة أرقام السيارات مرتّبة ترتيباً طبيعياً تصاعدياً."""
    return sorted({str(v).strip() for v in values if str(v).strip()},
                  key=plate_sort_key)


def numeric_plate_column(df: pd.DataFrame, col: str = "رقم السيارة") -> pd.DataFrame:
    """يحوّل عمود رقم السيارة لنوع عددي صحيح متى أمكن، وإلا يرتّبه ترتيباً
    طبيعياً عبر نوع Categorical مرتَّب — لا يُغيّر أي قيمة، فقط طريقة الفرز
    والعرض."""
    if df is None or len(df) == 0 or col not in df.columns:
        return df
    df = df.copy()
    s = df[col].astype(str).str.strip()
    if len(s) and s.str.fullmatch(r"-?\d+").all():
        df[col] = pd.to_numeric(s, errors="coerce").astype("Int64")
    else:
        categories = sort_plates(s.unique().tolist())
        df[col] = pd.Categorical(s, categories=categories, ordered=True)
    return df


def sort_by_plate(df: pd.DataFrame, col: str = "رقم السيارة",
                  ascending: bool = True) -> pd.DataFrame:
    """يُرجع نسخة من الجدول مرتّبة تصاعدياً (افتراضياً) حسب رقم السيارة
    ترتيباً طبيعياً عددياً، بغضّ النظر عن كون العمود نصاً أو رقماً."""
    if df is None or len(df) == 0 or col not in df.columns:
        return df
    order = sorted(range(len(df)),
                   key=lambda i: plate_sort_key(df[col].iloc[i]),
                   reverse=not ascending)
    return df.iloc[order].reset_index(drop=True)


# ---------------------------------------------------------------------------
# استيراد كشوف الحركة المرفوعة (Excel / CSV) إلى سجلات قابلة للحفظ
# ---------------------------------------------------------------------------
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# أسماء بديلة شائعة لكل عمود أساسي — تُطابَق بعد التوحيد أدناه، فيقبل
# التطبيق كشفاً موسوماً بأي تسمية مألوفة للعمود نفسه دون أن يفشل الاستيراد.
_IMPORT_ALIASES = {
    "التاريخ": ["التاريخ", "تاريخ", "اليوم"],
    "رقم السيارة": ["رقم السيارة", "رقم الشاحنة", "رقم المركبة",
                     "الشاحنة", "السيارة"],
    "عدد الزفات": ["عدد الزفات", "الزفات", "عدد الكشفات"],
    "تفاصيل الزفات": ["تفاصيل الزفات", "التفاصيل", "وصف الحركة"],
    "المسافة المقطوعة (كم)": ["المسافة المقطوعة (كم)", "المسافة (كم)",
                                "المسافة بالكيلومتر", "المسافة", "المسافه"],
    "الوقت المستغرق": ["الوقت المستغرق", "الوقت", "المدة", "زمن العمل"],
}


def _header_key(value) -> str:
    """مفتاح موحّد لمقارنة رؤوس الأعمدة: الأرقام العربية ← إنجليزية،
    توحيد الهمزة والتاء المفتوحة/المربوطة والألف المقصورة، وحذف المسافات
    والترقيم — فلا يفشل المطابقة بسبب فرق تشكيل أو مسافة زائدة."""
    s = str(value if value is not None else "").strip().translate(_ARABIC_DIGITS)
    s = s.replace("\u200f", "").replace("\u200e", "").replace("\ufeff", "")
    s = re.sub(r"[إأآٱ]", "ا", s)
    s = s.replace("ة", "ه").replace("ى", "ي")
    return re.sub(r"\W+", "", s)


def _text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _number(value):
    """يستخرج رقماً من أي خلية (رقم، نص «1400 كم»، رقم عربي ١٤٠٠...).
    يُرجع None إن لم يكن فيها رقم أصلاً."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    s = str(value).strip().translate(_ARABIC_DIGITS)
    if not s or s.lower() in ("nan", "none", "nat"):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s.replace(",", ""))
    return float(m.group()) if m else None


def _date_value(value, fallback: str) -> str:
    """يُرجع تاريخاً بصيغة ISO (YYYY-MM-DD) من خلية أو كائن تاريخ،
    أو تاريخ الرجوع إن كانت الخلية فارغة/غير قابلة للقراءة."""
    if value is None:
        return fallback
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()[:10]
        except Exception:
            return fallback
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return fallback
    parsed = pd.to_datetime(s, errors="coerce")
    try:
        if pd.isna(parsed):
            return fallback
    except (TypeError, ValueError):
        return fallback
    return parsed.date().isoformat()


def parse_imported_df(df, entry_date=None) -> list:
    """
    يحوّل جدولاً مرفوعاً (Excel / CSV) بأعمدة معروفة إلى قائمة سجلات جاهزة
    للحفظ عبر ``storage.add_records``.

    تُطابق الأعمدة بأسمائها العربية بعد التوحيد أعلاه، وتعتمد تاريخ الإدخال
    ``entry_date`` حين لا يحتوي الملف عمود تاريخ. تعود بقائمة فارغة إن لم
    يجد عمودي «رقم السيارة» و«المسافة المقطوعة (كم)» — عندها تعرض app.py
    رسالة توضيحية للمستخدم بدل رمي استثناء.
    """
    if not isinstance(df, pd.DataFrame) or len(df) == 0:
        return []

    available = {}
    for col in df.columns:
        available.setdefault(_header_key(col), col)

    columns = {}
    for canonical, aliases in _IMPORT_ALIASES.items():
        for alias in aliases:
            source = available.get(_header_key(alias))
            if source is not None:
                columns[canonical] = source
                break

    if "رقم السيارة" not in columns or "المسافة المقطوعة (كم)" not in columns:
        return []

    default_date = _date_value(entry_date, date.today().isoformat())
    rows = []
    for _, raw in df.iterrows():
        plate = _text(raw.get(columns["رقم السيارة"]))
        if not plate or plate.lower() in ("nan", "none"):
            continue
        km = _number(raw.get(columns["المسافة المقطوعة (كم)"]))
        if km is None:
            continue
        zfat = 0
        if "عدد الزفات" in columns:
            zfat_raw = _number(raw.get(columns["عدد الزفات"]))
            zfat = max(0, int(zfat_raw)) if zfat_raw is not None else 0
        details = _text(raw.get(columns["تفاصيل الزفات"])) if "تفاصيل الزفات" in columns else ""
        spent = _text(raw.get(columns["الوقت المستغرق"])) if "الوقت المستغرق" in columns else ""
        row_date = default_date
        if "التاريخ" in columns:
            row_date = _date_value(raw.get(columns["التاريخ"]), default_date)
        rows.append({
            "التاريخ": row_date,
            "رقم السيارة": plate,
            "عدد الزفات": zfat,
            "تفاصيل الزفات": details or "غير محدد",
            "المسافة المقطوعة (كم)": round(max(0.0, km), 2),
            "الوقت المستغرق": spent or "غير محدد",
        })
    return rows
