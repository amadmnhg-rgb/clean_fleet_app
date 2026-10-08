# -*- coding: utf-8 -*-
"""
وحدة التحقق من صحة البيانات.

توفر دوال للتحقق من صحة المدخلات قبل الحفظ في قاعدة البيانات.
"""

from datetime import date, datetime
from typing import Dict, Any, Tuple


def validate_plate(plate: str) -> Tuple[bool, str]:
    """التحقق من صحة رقم السيارة."""
    if not plate or not str(plate).strip():
        return False, "رقم السيارة مطلوب"
    plate = str(plate).strip()
    if len(plate) > 20:
        return False, "رقم السيارة طويل جداً"
    return True, ""


def validate_distance(distance: float) -> Tuple[bool, str]:
    """التحقق من صحة المسافة المقطوعة."""
    try:
        dist = float(distance)
        if dist < 0:
            return False, "المسافة لا يمكن أن تكون سالبة"
        if dist > 10000:  # 10,000 كم كحد أقصى معقول ليوم واحد
            return False, "المسافة كبيرة جداً لرحلة واحدة"
        return True, ""
    except (TypeError, ValueError):
        return False, "المسافة يجب أن تكون رقماً"


def validate_zafat_count(count: int) -> Tuple[bool, str]:
    """التحقق من صحة عدد الزفات."""
    try:
        zafat = int(count)
        if zafat < 0:
            return False, "عدد الزفات لا يمكن أن يكون سالباً"
        if zafat > 100:  # حد معقول
            return False, "عدد الزفات كبير جداً"
        return True, ""
    except (TypeError, ValueError):
        return False, "عدد الزفات يجب أن يكون رقماً صحيحاً"


def validate_date(date_str: str) -> Tuple[bool, str]:
    """التحقق من صحة التاريخ."""
    if not date_str:
        return False, "التاريخ مطلوب"
    try:
        # محاولة تحويل التاريخ إلى ISO
        if isinstance(date_str, date):
            date_str = date_str.isoformat()
        parsed = datetime.fromisoformat(str(date_str))
        # التحقق من أن التاريخ ليس في المستقبل البعيد
        today = date.today()
        future_limit = today.replace(year=today.year + 1)
        if parsed.date() > future_limit:
            return False, "التاريخ في المستقبل البعيد"
        # التحقق من أن التاريخ ليس في الماضي البعيد جداً
        past_limit = today.replace(year=today.year - 10)
        if parsed.date() < past_limit:
            return False, "التاريخ قديم جداً"
        return True, ""
    except (ValueError, TypeError):
        return False, "صيغة التاريخ غير صحيحة"


def validate_record(record: Dict[str, Any]) -> Tuple[bool, list]:
    """
    التحقق من صحة سجل كامل.
    يُرجع: (هل صحيح؟, قائمة بالأخطاء)
    """
    errors = []

    # التحقق من الحقول المطلوبة
    if "رقم السيارة" not in record or not record["رقم السيارة"]:
        errors.append("رقم السيارة مطلوب")
    else:
        valid, msg = validate_plate(record["رقم السيارة"])
        if not valid:
            errors.append(msg)

    if "المسافة المقطوعة (كم)" in record:
        valid, msg = validate_distance(record["المسافة المقطوعة (كم)"])
        if not valid:
            errors.append(msg)

    if "عدد الزفات" in record:
        valid, msg = validate_zafat_count(record["عدد الزفات"])
        if not valid:
            errors.append(msg)

    if "التاريخ" in record:
        valid, msg = validate_date(record["التاريخ"])
        if not valid:
            errors.append(msg)

    return len(errors) == 0, errors


def sanitize_text(text: str, max_length: int = 500) -> str:
    """تنظيف النصوص من المحتوى الخطير."""
    if not text:
        return ""
    text = str(text).strip()
    # إزالة الأحرف الخاصة الخطرة
    dangerous_chars = ['<', '>', '&', '"', "'", '\x00']
    for char in dangerous_chars:
        text = text.replace(char, '')
    # قص النص إذا كان طويلاً جداً
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text
