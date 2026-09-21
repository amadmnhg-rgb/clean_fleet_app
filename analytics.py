# -*- coding: utf-8 -*-
"""
وحدة التحليلات والرسوم البيانية.

كل الدوال هنا خالصة (pure) وتعمل مباشرة على جدول السجلات (fleet_data)
دون أي تعديل أو تخمين للبيانات — التجميع فقط حسب ما هو مسجَّل فعلياً.

الفترات المدعومة: "يومي" (تاريخ كامل)، "شهري" (YYYY-MM)، "سنوي" (YYYY).
التواريخ في النظام مضمونة بصيغة ISO (YYYY-MM-DD)، لذا يكفي اقتطاع النص.
"""

from __future__ import annotations

import pandas as pd

from . import util

PERIODS = ["يومي", "شهري", "سنوي"]
_SLICE_LEN = {"يومي": 10, "شهري": 7, "سنوي": 4}


def period_key(date_value: str, period: str) -> str:
    """يحوّل تاريخاً بصيغة ISO إلى مفتاح الفترة المطلوبة."""
    return str(date_value)[: _SLICE_LEN.get(period, 10)]


def _period_series(dates: pd.Series, period: str) -> pd.Series:
    return dates.astype(str).str.slice(0, _SLICE_LEN.get(period, 10))


def operations_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """عدد العمليات (السجلات) وإجمالي المسافة والزفات لكل فترة زمنية."""
    columns = ["الفترة", "عدد العمليات", "إجمالي المسافة (كم)", "إجمالي الزفات"]
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=columns)
    d = df.copy()
    d["الفترة"] = _period_series(d["التاريخ"], period)
    grouped = d.groupby("الفترة").agg(**{
        "عدد العمليات": ("رقم السيارة", "count"),
        "إجمالي المسافة (كم)": ("المسافة المقطوعة (كم)", "sum"),
        "إجمالي الزفات": ("عدد الزفات", "sum"),
    }).reset_index()
    grouped["إجمالي المسافة (كم)"] = grouped["إجمالي المسافة (كم)"].round(1)
    return grouped.sort_values("الفترة").reset_index(drop=True)


def usage_by_vehicle(df: pd.DataFrame, top_n: int = None) -> pd.DataFrame:
    """ترتيب السيارات حسب الاستخدام الفعلي (المسافة وعدد العمليات والزفات)."""
    columns = ["رقم السيارة", "عدد العمليات", "إجمالي المسافة (كم)", "إجمالي الزفات"]
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=columns)
    d = df.copy()
    grouped = d.groupby("رقم السيارة").agg(**{
        "عدد العمليات": ("التاريخ", "count"),
        "إجمالي المسافة (كم)": ("المسافة المقطوعة (كم)", "sum"),
        "إجمالي الزفات": ("عدد الزفات", "sum"),
    }).reset_index()
    grouped["إجمالي المسافة (كم)"] = grouped["إجمالي المسافة (كم)"].round(1)
    grouped = grouped.sort_values("إجمالي المسافة (كم)", ascending=False).reset_index(drop=True)
    if top_n:
        grouped = grouped.head(top_n)
    return grouped


def period_values(df: pd.DataFrame, period: str) -> list:
    """كل قيم الفترة الموجودة فعلياً في البيانات (مرتبة تنازلياً)."""
    if df is None or len(df) == 0:
        return []
    return sorted(_period_series(df["التاريخ"], period).unique().tolist(),
                 reverse=True)


def filter_by_period_value(df: pd.DataFrame, period: str, value: str) -> pd.DataFrame:
    """يُرجع فقط السجلات الواقعة ضمن قيمة فترة محددة (مثال: '2026-09')."""
    if df is None or len(df) == 0 or not value:
        return df
    mask = _period_series(df["التاريخ"], period) == value
    return df[mask]


def compare_vehicles(df: pd.DataFrame, plates: list, period: str,
                     metric: str = "المسافة المقطوعة (كم)") -> pd.DataFrame:
    """جدول محوري (الفترة × السيارات) لمقارنة استخدام عدة سيارات فعلياً."""
    if df is None or len(df) == 0 or not plates:
        return pd.DataFrame()
    plate_set = {str(p) for p in plates}
    d = df[df["رقم السيارة"].astype(str).isin(plate_set)].copy()
    if len(d) == 0:
        return pd.DataFrame()
    d["الفترة"] = _period_series(d["التاريخ"], period)
    pivot = d.pivot_table(index="الفترة", columns="رقم السيارة", values=metric,
                          aggfunc="sum", fill_value=0)
    ordered_cols = [c for c in util.sort_plates(pivot.columns) if c in pivot.columns]
    pivot = pivot[ordered_cols]
    return pivot.sort_index()


def comparison_totals(df: pd.DataFrame, plates: list) -> pd.DataFrame:
    """إجمالي المسافة وعدد العمليات لكل سيارة من السيارات المختارة للمقارنة."""
    columns = ["رقم السيارة", "إجمالي المسافة (كم)", "عدد العمليات", "إجمالي الزفات"]
    if df is None or len(df) == 0 or not plates:
        return pd.DataFrame(columns=columns)
    plate_set = {str(p) for p in plates}
    d = df[df["رقم السيارة"].astype(str).isin(plate_set)].copy()
    if len(d) == 0:
        return pd.DataFrame(columns=columns)
    grouped = d.groupby("رقم السيارة").agg(**{
        "إجمالي المسافة (كم)": ("المسافة المقطوعة (كم)", "sum"),
        "عدد العمليات": ("التاريخ", "count"),
        "إجمالي الزفات": ("عدد الزفات", "sum"),
    }).reset_index()
    grouped["إجمالي المسافة (كم)"] = grouped["إجمالي المسافة (كم)"].round(1)
    return grouped.sort_values("إجمالي المسافة (كم)", ascending=False).reset_index(drop=True)
