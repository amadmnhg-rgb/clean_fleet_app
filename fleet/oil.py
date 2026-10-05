# -*- coding: utf-8 -*-
"""
محرك حساب عداد الزيت بنظام الدورات المستقلة.

قواعد الحساب (كما هي مطلوبة تماماً):
1. كل سيارة تبدأ عدادها من الصفر.
2. يُجمع عليه ما تقطعه السيارة (مسافة × معامل) تراكمياً.
3. عند بلوغ الحد المحدد من قِبل المستخدم (2500 كم افتراضياً) يظهر تنبيه واضح.
4. العداد لا يتجاوز الحد أبداً: يتوقف عند القيمة القصوى (لا يُكتب 2560).
5. بعد اعتماد تغيير الزيت تُغلق الدورة وتبدأ دورة جديدة من الصفر،
   وكل دورة مستقلة تماماً عن سابقتها (لا يُرحَّل أي فائض).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date


@dataclass
class OilCycle:
    """حالة دورة الزيت الحالية لسيارة واحدة."""

    plate: str
    cycle: int = 1
    counter: float = 0.0
    limit: float = 2500.0
    start_date: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def add_distance(counter: float, limit: float, distance: float,
                 factor: float = 1.0) -> tuple:
    """
    يضيف المسافة إلى عداد الدورة الحالية دون تجاوز الحد.

    يُرجع: (العداد الجديد, هل بلغ الحد؟, المقدار الذي تم تجاهله لتجاوزه الحد)
    """
    counter = max(0.0, float(counter or 0.0))
    limit = max(1.0, float(limit or 1.0))
    added = max(0.0, float(distance or 0.0)) * float(factor or 1.0)

    raw_total = counter + added
    if raw_total >= limit:
        return round(limit, 2), True, round(raw_total - limit, 2)
    return round(raw_total, 2), False, 0.0


def subtract_distance(counter: float, distance: float,
                      factor: float = 1.0) -> float:
    """يخصم مسافة سجل محذوف من عداد الدورة الحالية (لا يقل عن صفر)."""
    counter = max(0.0, float(counter or 0.0))
    removed = max(0.0, float(distance or 0.0)) * float(factor or 1.0)
    return round(max(0.0, counter - removed), 2)


def reset_cycle(state: OilCycle, new_limit: float = None,
                on_date: str = None) -> OilCycle:
    """يغلق الدورة الحالية ويبدأ دورة جديدة من الصفر (مستقلة تماماً)."""
    today = on_date or date.today().isoformat()
    state.cycle = int(state.cycle or 1) + 1
    state.counter = 0.0
    if new_limit:
        state.limit = float(new_limit)
    state.start_date = today
    state.updated_at = today
    return state


def cycle_status(counter: float, limit: float, near_ratio: float = 0.9) -> str:
    """يُرجع حالة السيارة: متجاوزة / قريبة / سليمة."""
    counter = float(counter or 0.0)
    limit = max(1.0, float(limit or 1.0))
    if counter >= limit:
        return "بلغت الحد"
    if counter >= limit * near_ratio:
        return "قريبة من الحد"
    return "سليمة"


def remaining_km(counter: float, limit: float) -> float:
    """المتبقي من الدورة الحالية بالكيلومتر."""
    return round(max(0.0, float(limit or 0.0) - float(counter or 0.0)), 2)


def progress_ratio(counter: float, limit: float) -> float:
    """نسبة إنجاز الدورة الحالية بين 0 و 1."""
    limit = max(1.0, float(limit or 1.0))
    return min(1.0, max(0.0, float(counter or 0.0) / limit))
