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
