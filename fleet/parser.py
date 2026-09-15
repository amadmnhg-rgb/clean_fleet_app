# -*- coding: utf-8 -*-
"""
محرك استخلاص رسائل الحركة اليومية (Regex Parser).

يقرأ النصوص الحرة وتقارير السائقين كما تُرسل في الواتساب ويستخرج منها:
  * رقم السيارة      (سيارة رقم 12 / شاحنة رقم 7 / مركبة رقم ك-3)
  * المسافة المقطوعة (المسافه 120 كم / 120 كم)
  * الوقت المستغرق   (الوقت من 7 الى 12 / المدة 5 ساعات)
  * عدد الزفات وتفاصيلها (الزفات 3 / تفاصيل الزفات: حي السلام، السوق، المستشفى)
  * التاريخ إن وُجد داخل الرسالة
"""

from __future__ import annotations

import re
from datetime import date

# ---------------------------------------------------------------------------
# أدوات التطبيع
# ---------------------------------------------------------------------------
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize(text: str) -> str:
    """توحيد الأرقام والحروف العربية لتسهيل المطابقة."""
    if not text:
        return ""
    text = str(text).translate(_AR_DIGITS)
    text = text.replace("ـ", "")
    text = re.sub(r"[إأآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"[\u064B-\u0652]", "", text)          # التشكيل
    text = text.replace("\u200f", "").replace("\u200e", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# التعابير النمطية
# ---------------------------------------------------------------------------
VEHICLE_WORDS = r"(?:سياره|شاحنه|مركبه|قلاب|كباس|لودر|باص|وايت)"

RE_VEHICLE = re.compile(
    VEHICLE_WORDS + r"\s*(?:رقم)?\s*[:\-]?\s*([A-Za-z0-9\u0621-\u064A][A-Za-z0-9\u0621-\u064A/\-]{0,11})"
)

RE_DISTANCE_LABELED = re.compile(
    r"(?:المسافه|مسافه|المسافه المقطوعه)\s*(?:المقطوعه)?\s*[:\-]?\s*([0-9]+(?:[.,][0-9]+)?)"
)
RE_DISTANCE_UNIT = re.compile(r"([0-9]+(?:[.,][0-9]+)?)\s*(?:كم|كيلو ?متر|كيلو|km|KM)")

RE_ZAFAT_LABELED = re.compile(r"(?:عدد\s*الزفات|الزفات|زفات|زفه)\s*[:\-]?\s*([0-9]+)")
RE_ZAFAT_REVERSE = re.compile(r"([0-9]+)\s*(?:زفات|زفه|زفه)")

RE_ZAFAT_DETAILS = re.compile(
    r"(?:تفاصيل\s*الزفات|تفاصيل|مسار الزفات|المواقع|الاحياء)\s*[:\-]?\s*(.+)"
)
RE_ZAFAT_LINE = re.compile(r"(?:الزفات|زفات)\s*[:\-]\s*([^\n0-9].*)")

RE_TIME_LABELED = re.compile(
    r"(?:الوقت\s*المستغرق|الوقت|المده|مده\s*العمل|ساعات\s*العمل|الدوام)\s*[:\-]?\s*(.+)"
)
RE_TIME_RANGE = re.compile(
    r"(من\s*[0-9]{1,2}(?::[0-9]{2})?\s*\S*\s*(?:الي|إلى|الى|حتي|-)\s*[0-9]{1,2}(?::[0-9]{2})?\s*\S*)"
)
RE_TIME_HOURS = re.compile(r"([0-9]{1,2}(?:[.,][0-9]{1,2})?\s*(?:ساعه|ساعات|ساعة))")

RE_DATE = re.compile(
    r"(?:التاريخ|بتاريخ|تاريخ)\s*[:\-]?\s*([0-9]{1,4}[/\-][0-9]{1,2}[/\-][0-9]{1,4})"
)

_SPLIT_PATTERN = re.compile(
    r"(?=" + VEHICLE_WORDS + r"\s*(?:رقم)?\s*[:\-]?\s*[A-Za-z0-9\u0621-\u064A])"
)


# ---------------------------------------------------------------------------
# أدوات مساعدة
# ---------------------------------------------------------------------------
def _to_float(value: str) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _normalize_date(raw: str, fallback: str) -> str:
    """تحويل التاريخ المكتوب داخل الرسالة إلى صيغة YYYY-MM-DD."""
    if not raw:
        return fallback
    parts = re.split(r"[/\-]", raw.strip())
    if len(parts) != 3:
        return fallback
    try:
        a, b, c = (int(p) for p in parts)
    except ValueError:
        return fallback
    if a > 31:                       # صيغة سنة/شهر/يوم
        y, m, d = a, b, c
    else:                            # صيغة يوم/شهر/سنة
        d, m, y = a, b, c
    if y < 100:
        y += 2000
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return fallback


def _clean_tail(text: str) -> str:
    """تنظيف نهاية السطر المستخرج من الكلمات الزائدة."""
    text = text.strip(" .،,:-|")
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _extract_details(block: str) -> str:
    for pattern in (RE_ZAFAT_DETAILS, RE_ZAFAT_LINE):
        match = pattern.search(block)
        if match:
            value = _clean_tail(match.group(1).split("\n")[0])
            if value and not value.isdigit():
                return value
    return ""


def _count_from_details(details: str) -> int:
    if not details:
        return 0
    parts = [p for p in re.split(r"[،,+\-/|]| ثم ", details) if p.strip()]
    return len(parts) if len(parts) > 1 else (1 if details else 0)


def _extract_time(block: str) -> str:
    match = RE_TIME_RANGE.search(block)
    if match:
        return _clean_tail(match.group(1))
    match = RE_TIME_LABELED.search(block)
    if match:
        value = _clean_tail(match.group(1).split("\n")[0])
        if value:
            return value
    match = RE_TIME_HOURS.search(block)
    if match:
        return _clean_tail(match.group(1))
    return "غير محدد"


def _extract_distance(block: str) -> float:
    match = RE_DISTANCE_LABELED.search(block)
    if match:
        return _to_float(match.group(1))
    match = RE_DISTANCE_UNIT.search(block)
    if match:
        return _to_float(match.group(1))
    return 0.0


def _extract_zafat(block: str, details: str) -> int:
    match = RE_ZAFAT_LABELED.search(block)
    if match:
        return int(_to_float(match.group(1)))
    match = RE_ZAFAT_REVERSE.search(block)
    if match:
        return int(_to_float(match.group(1)))
    return _count_from_details(details)


# ---------------------------------------------------------------------------
# الدالة الرئيسية
# ---------------------------------------------------------------------------
def parse_daily_fleet_messages(raw_text: str, default_date: str = None) -> list:
    """
    يحلل نص التقارير اليومية ويُرجع قائمة من القواميس، لكل سيارة سجل واحد:
    {التاريخ, رقم السيارة, عدد الزفات, تفاصيل الزفات,
     المسافة المقطوعة (كم), الوقت المستغرق}
    """
    fallback_date = default_date or date.today().isoformat()
    text = normalize(raw_text)
    if not text:
        return []

    global_date = fallback_date
    gmatch = RE_DATE.search(text)
    if gmatch:
        global_date = _normalize_date(gmatch.group(1), fallback_date)

    blocks = [b.strip() for b in _SPLIT_PATTERN.split(text) if b and b.strip()]
    results = []

    for block in blocks:
        vmatch = RE_VEHICLE.search(block)
        if not vmatch:
            continue
        plate = _clean_tail(vmatch.group(1))
        if not plate:
            continue

        bmatch = RE_DATE.search(block)
        row_date = _normalize_date(bmatch.group(1), global_date) if bmatch else global_date

        details = _extract_details(block)
        distance = _extract_distance(block)
        zafat = _extract_zafat(block, details)
        time_taken = _extract_time(block)

        results.append({
            "التاريخ": row_date,
            "رقم السيارة": plate,
            "عدد الزفات": int(zafat),
            "تفاصيل الزفات": details or "غير محدد",
            "المسافة المقطوعة (كم)": round(distance, 2),
            "الوقت المستغرق": time_taken,
        })

    return results
