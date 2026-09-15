# -*- coding: utf-8 -*-
"""
تطبيق إدارة أسطول الشاحنات والزيوت
صندوق النظافة والتحسين - محافظة المهرة

التشغيل:  streamlit run app.py
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime

import pandas as pd
import streamlit as st

from fleet import styles
from fleet.config import (
    ALL_COLUMNS,
    APP_ICON,
    APP_TITLE,
    APP_VERSION,
    BASE_COLUMNS,
    DEFAULT_OIL_FACTOR,
    DEFAULT_OIL_LIMIT,
    NEAR_LIMIT_RATIO,
    OIL_STATE_COLUMNS,
    ORG_NAME,
)
from fleet.oil import (
    add_distance,
    cycle_status,
    progress_ratio,
    remaining_km,
    subtract_distance,
)
from fleet.parser import parse_daily_fleet_messages
from fleet.storage import build_storage, coerce_records, empty_records_df

# ---------------------------------------------------------------------------
# 1) إعدادات الصفحة والبيئة
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(styles.CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 2) طبقة التخزين (Google Sheets تلقائياً مع تخزين محلي احتياطي)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="جارٍ تهيئة قاعدة البيانات…")
def get_storage():
    try:
        secrets = dict(st.secrets)
    except Exception:  # noqa: BLE001
        secrets = {}
    return build_storage(secrets)


STORAGE, STORAGE_MSG, IS_CLOUD = get_storage()


# ---------------------------------------------------------------------------
# 3) نظام الجلسات (Session State)
# ---------------------------------------------------------------------------
def init_session():
    ss = st.session_state
    ss.setdefault("logged_in", True)
    ss.setdefault("undo_stack", [])
    ss.setdefault("flash", None)

    if "settings" not in ss:
        saved = STORAGE.load_settings()
        ss.settings = {
            "oil_limit": float(saved.get("oil_limit", DEFAULT_OIL_LIMIT)),
            "oil_factor": float(saved.get("oil_factor", DEFAULT_OIL_FACTOR)),
        }
    if "fleet_data" not in ss:
        ss.fleet_data = STORAGE.load_records()
    if "oil_state" not in ss:
        ss.oil_state = STORAGE.load_oil_state()


def reload_from_storage():
    st.session_state.fleet_data = STORAGE.load_records()
    st.session_state.oil_state = STORAGE.load_oil_state()


init_session()

OIL_LIMIT = float(st.session_state.settings["oil_limit"])
OIL_FACTOR = float(st.session_state.settings["oil_factor"])
TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# 4) إدارة دورات الزيت
# ---------------------------------------------------------------------------
def state_map() -> dict:
    """تحويل جدول حالات الزيت إلى قاموس {رقم السيارة: الحالة}."""
    df = st.session_state.oil_state
    result = {}
    if df is None or len(df) == 0:
        return result
    for _, row in df.iterrows():
        plate = str(row["رقم السيارة"]).strip()
        if not plate:
            continue
        result[plate] = {
            "رقم السيارة": plate,
            "دورة الزيت": int(float(row["دورة الزيت"] or 1)),
            "عداد الدورة": float(row["عداد الدورة"] or 0),
            "حد تغيير الزيت": float(row["حد تغيير الزيت"] or OIL_LIMIT),
            "تاريخ بداية الدورة": str(row["تاريخ بداية الدورة"] or TODAY),
            "آخر تحديث": str(row["آخر تحديث"] or TODAY),
        }
    return result


def save_state_map(mapping: dict):
    df = pd.DataFrame(list(mapping.values()))
    if len(df) == 0:
        df = pd.DataFrame(columns=OIL_STATE_COLUMNS)
    df = df[OIL_STATE_COLUMNS]
    st.session_state.oil_state = df
    STORAGE.save_oil_state(df)


def ensure_state(mapping: dict, plate: str) -> dict:
    if plate not in mapping:
        mapping[plate] = {
            "رقم السيارة": plate,
            "دورة الزيت": 1,
            "عداد الدورة": 0.0,
            "حد تغيير الزيت": OIL_LIMIT,
            "تاريخ بداية الدورة": TODAY,
            "آخر تحديث": TODAY,
        }
    return mapping[plate]


def close_cycle(plate: str, on_date: str = None, note: str = "تم تغيير الزيت"):
    """إغلاق الدورة الحالية وبدء دورة جديدة من الصفر (مستقلة تماماً)."""
    mapping = state_map()
    state = ensure_state(mapping, plate)
    day = on_date or TODAY
    STORAGE.append_oil_log({
        "التاريخ": day,
        "رقم السيارة": plate,
        "الدورة المنتهية": state["دورة الزيت"],
        "العداد عند الإغلاق": state["عداد الدورة"],
        "الحد المعتمد": state["حد تغيير الزيت"],
        "ملاحظة": note,
    })
    state["دورة الزيت"] = int(state["دورة الزيت"]) + 1
    state["عداد الدورة"] = 0.0
    state["حد تغيير الزيت"] = OIL_LIMIT
    state["تاريخ بداية الدورة"] = day
    state["آخر تحديث"] = day
    save_state_map(mapping)


# ---------------------------------------------------------------------------
# 5) عمليات البيانات
# ---------------------------------------------------------------------------
def add_batch(rows: list) -> dict:
    """إضافة دفعة سجلات مع تحديث عدادات الزيت، وحفظ نقطة تراجع."""
    if not rows:
        return {"added": 0, "alerts": []}

    mapping = state_map()
    before_snapshot = {k: dict(v) for k, v in mapping.items()}
    batch_id = uuid.uuid4().hex[:10]
    prepared, alerts = [], []

    for row in rows:
        plate = str(row["رقم السيارة"]).strip()
        state = ensure_state(mapping, plate)
        limit = float(state["حد تغيير الزيت"] or OIL_LIMIT)
        counter, reached, dropped = add_distance(
            state["عداد الدورة"], limit,
            row.get("المسافة المقطوعة (كم)", 0), OIL_FACTOR)

        state["عداد الدورة"] = counter
        state["آخر تحديث"] = row.get("التاريخ", TODAY)

        prepared.append({
            "التاريخ": row.get("التاريخ", TODAY),
            "رقم السيارة": plate,
            "عدد الزفات": int(row.get("عدد الزفات", 0)),
            "تفاصيل الزفات": row.get("تفاصيل الزفات", "غير محدد"),
            "المسافة المقطوعة (كم)": float(row.get("المسافة المقطوعة (كم)", 0)),
            "الوقت المستغرق": row.get("الوقت المستغرق", "غير محدد"),
            "عداد الزيت الحالي": counter,
            "حد تغيير الزيت": limit,
            "دورة الزيت": int(state["دورة الزيت"]),
            "معرف السجل": uuid.uuid4().hex[:12],
            "رقم الدفعة": batch_id,
        })

        if reached:
            alerts.append({
                "plate": plate,
                "limit": limit,
                "cycle": int(state["دورة الزيت"]),
                "dropped": dropped,
            })

    STORAGE.append_records(prepared)
    save_state_map(mapping)
    st.session_state.fleet_data = coerce_records(
        pd.concat([st.session_state.fleet_data, pd.DataFrame(prepared)],
                  ignore_index=True))
    st.session_state.undo_stack.append({
        "batch_id": batch_id,
        "count": len(prepared),
        "time": datetime.now().strftime("%H:%M:%S"),
        "state_before": before_snapshot,
    })
    return {"added": len(prepared), "alerts": alerts, "batch_id": batch_id}


def undo_last_batch() -> int:
    """التراجع عن آخر إدخال مجمع واستعادة عدادات الزيت كما كانت."""
    if not st.session_state.undo_stack:
        return 0
    entry = st.session_state.undo_stack.pop()
    df = st.session_state.fleet_data
    keep = df[df["رقم الدفعة"] != entry["batch_id"]]
    removed = len(df) - len(keep)
    STORAGE.save_records(keep)
    st.session_state.fleet_data = coerce_records(keep)
    save_state_map(entry["state_before"])
    return removed


def delete_records(mask: pd.Series) -> int:
    """حذف سجلات محددة مع خصم مسافاتها من عدادات الدورة الحالية."""
    df = st.session_state.fleet_data
    target = df[mask]
    if len(target) == 0:
        return 0

    mapping = state_map()
    for _, row in target.iterrows():
        plate = str(row["رقم السيارة"]).strip()
        if plate not in mapping:
            continue
        state = mapping[plate]
        if int(row["دورة الزيت"] or 1) == int(state["دورة الزيت"]):
            state["عداد الدورة"] = subtract_distance(
                state["عداد الدورة"], row["المسافة المقطوعة (كم)"], OIL_FACTOR)
            state["آخر تحديث"] = TODAY

    keep = df[~mask]
    STORAGE.save_records(keep)
    st.session_state.fleet_data = coerce_records(keep)
    save_state_map(mapping)
    return len(target)


# ---------------------------------------------------------------------------
# 6) أدوات عرض
# ---------------------------------------------------------------------------
def fleet_overview() -> pd.DataFrame:
    """جدول حالة الزيت لكل سيارة في الأسطول."""
    mapping = state_map()
    rows = []
    for plate, state in mapping.items():
        counter = state["عداد الدورة"]
        limit = state["حد تغيير الزيت"]
        rows.append({
            "رقم السيارة": plate,
            "دورة الزيت": state["دورة الزيت"],
            "عداد الزيت الحالي": counter,
            "حد تغيير الزيت": limit,
            "المتبقي (كم)": remaining_km(counter, limit),
            "الحالة": cycle_status(counter, limit, NEAR_LIMIT_RATIO),
            "بداية الدورة": state["تاريخ بداية الدورة"],
            "آخر تحديث": state["آخر تحديث"],
        })
    if not rows:
        return pd.DataFrame(columns=[
            "رقم السيارة", "دورة الزيت", "عداد الزيت الحالي", "حد تغيير الزيت",
            "المتبقي (كم)", "الحالة", "بداية الدورة", "آخر تحديث"])
    return pd.DataFrame(rows).sort_values("عداد الزيت الحالي", ascending=False)


def show_table(df: pd.DataFrame, columns: list = None):
    if df is None or len(df) == 0:
        st.info("لا توجد بيانات لعرضها حتى الآن.")
        return
    view = df[columns] if columns else df
    st.dataframe(view, width="stretch", hide_index=True)


def flash():
    msg = st.session_state.get("flash")
    if msg:
        kind, text = msg
        getattr(st, kind)(text)
        st.session_state.flash = None


# ---------------------------------------------------------------------------
# 7) شاشة القفل
# ---------------------------------------------------------------------------
def lock_screen():
    st.markdown(
        '<div class="glass-panel lock-screen">'
        '<div class="lock-icon">🔒</div>'
        f'<h2>تم تسجيل الخروج بنجاح</h2>'
        f'<p>{ORG_NAME}</p></div>',
        unsafe_allow_html=True,
    )
    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("🔓 إعادة الدخول إلى النظام", width="stretch",
                     type="primary"):
            st.session_state.logged_in = True
            reload_from_storage()
            st.rerun()
    st.stop()


if not st.session_state.logged_in:
    lock_screen()


# ---------------------------------------------------------------------------
# 8) الشريط الجانبي
# ---------------------------------------------------------------------------
SECTIONS = [
    "📊 لوحة التحكم الرئيسية",
    "📝 الحركة اليومية (قراءة الرسائل)",
    "📋 السجل الشهري المجدول",
    "📁 السجل العام (Excel / CSV)",
    "⚙️ الإعدادات العامة والصيانة",
]

with st.sidebar:
    st.markdown(f"### {APP_ICON} {APP_TITLE}")
    st.caption(ORG_NAME)
    section = st.radio("الأقسام التشغيلية", SECTIONS, label_visibility="collapsed")
    st.divider()
    st.caption("🟢 متصل بـ Google Sheets" if IS_CLOUD else "🟡 تخزين محلي")
    st.caption(f"حد تغيير الزيت الحالي: **{OIL_LIMIT:,.0f} كم**")
    st.caption(f"إجمالي السجلات: **{len(st.session_state.fleet_data)}**")

flash()
data = st.session_state.fleet_data


# ---------------------------------------------------------------------------
# 9) القسم الأول: لوحة التحكم الرئيسية
# ---------------------------------------------------------------------------
def page_dashboard():
    st.markdown(styles.header(
        "📊 لوحة التحكم الرئيسية",
        f"متابعة حية لحالة الأسطول وعدادات الزيت — {TODAY}"),
        unsafe_allow_html=True)

    overview = fleet_overview()
    today_rows = data[data["التاريخ"] == TODAY] if len(data) else empty_records_df()

    over_limit = int((overview["الحالة"] == "بلغت الحد").sum()) if len(overview) else 0
    near_limit = int((overview["الحالة"] == "قريبة من الحد").sum()) if len(overview) else 0
    today_km = float(today_rows["المسافة المقطوعة (كم)"].sum()) if len(today_rows) else 0.0
    moving_today = int(today_rows["رقم السيارة"].nunique()) if len(today_rows) else 0
    total_fleet = int(overview["رقم السيارة"].nunique()) if len(overview) else 0

    cards = [
        ("🛢️", over_limit, "سيارات بلغت حد الزيت", "danger"),
        ("⚠️", near_limit, "تحتاج صيانة قريباً", "warning"),
        ("🛣️", f"{today_km:,.0f}", "إجمالي مسافة اليوم (كم)", "ok"),
        ("🚚", moving_today, "الشاحنات المتحركة اليوم", "ok"),
        ("🚛", total_fleet, "إجمالي الأسطول", "ok"),
    ]
    cols = st.columns(len(cards))
    for col, (icon, value, label, tone) in zip(cols, cards):
        with col:
            st.markdown(styles.stat_card(icon, value, label, tone),
                        unsafe_allow_html=True)

    # تنبيهات بلوغ الحد
    if len(overview):
        reached = overview[overview["الحالة"] == "بلغت الحد"]
        if len(reached):
            st.error(f"🚨 تنبيه: {len(reached)} سيارة بلغت حد تغيير الزيت "
                     f"({OIL_LIMIT:,.0f} كم). يجب تغيير الزيت ثم إغلاق الدورة "
                     "لتبدأ دورة جديدة من الصفر.")
            for _, row in reached.iterrows():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(
                        f'<div class="glass-panel">🚛 <b>السيارة {row["رقم السيارة"]}</b> — '
                        f'الدورة رقم {int(row["دورة الزيت"])} — '
                        f'العداد: <b>{row["عداد الزيت الحالي"]:,.0f}</b> / '
                        f'{row["حد تغيير الزيت"]:,.0f} كم '
                        f'<span class="badge badge-danger">بلغت الحد</span></div>',
                        unsafe_allow_html=True)
                with c2:
                    if st.button("✅ تم تغيير الزيت",
                                 key=f"reset_{row['رقم السيارة']}",
                                 width="stretch"):
                        close_cycle(str(row["رقم السيارة"]))
                        st.session_state.flash = (
                            "success",
                            f"تم إغلاق دورة السيارة {row['رقم السيارة']} "
                            "وبدأت دورة جديدة من الصفر.")
                        st.rerun()

    st.subheader("🛢️ حالة عدادات الزيت (الدورة الحالية)")
    if len(overview):
        show_table(overview)
        for _, row in overview.head(8).iterrows():
            ratio = progress_ratio(row["عداد الزيت الحالي"], row["حد تغيير الزيت"])
            st.progress(ratio, text=(
                f'السيارة {row["رقم السيارة"]} — '
                f'{row["عداد الزيت الحالي"]:,.0f} / {row["حد تغيير الزيت"]:,.0f} كم '
                f'(دورة {int(row["دورة الزيت"])})'))
    else:
        st.info("لا توجد سيارات مسجلة بعد. ابدأ من قسم «الحركة اليومية».")

    st.subheader("📄 السجلات الحية لليوم")
    show_table(today_rows, BASE_COLUMNS)


# ---------------------------------------------------------------------------
# 10) القسم الثاني: الحركة اليومية (قراءة الرسائل)
# ---------------------------------------------------------------------------
SAMPLE = """التاريخ: {today}
سيارة رقم 12 المسافه 140 كم الوقت من 7 الى 12 الزفات 3
تفاصيل الزفات: حي السلام، السوق المركزي، المستشفى

شاحنة رقم 7 المسافه 95 كم الوقت 5 ساعات
تفاصيل الزفات: الحي الشرقي، مخيم النزوح
""".format(today=TODAY)


def page_daily():
    st.markdown(styles.header(
        "📝 الحركة اليومية (قراءة الرسائل)",
        "الصق تقارير السائقين كما هي وسيقوم النظام بتحليلها آلياً"),
        unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        entry_date = st.date_input("تاريخ الحركة", value=date.today(),
                                   format="YYYY-MM-DD")
    with c2:
        st.text_input("حد تغيير الزيت المعتمد حالياً (كم)",
                      value=f"{OIL_LIMIT:,.0f}", disabled=True)

    raw = st.text_area(
        "نص رسائل الحركة اليومية",
        height=230,
        placeholder=SAMPLE,
        help="مثال: سيارة رقم 12 المسافه 140 كم الوقت من 7 الى 12 الزفات 3",
    )

    b1, b2, b3 = st.columns([2, 1, 1])
    with b1:
        analyze = st.button("🔍 تحليل وحفظ الرسائل", type="primary",
                            width="stretch")
    with b2:
        preview = st.button("👁️ معاينة فقط", width="stretch")
    with b3:
        undo = st.button("↩️ تراجع عن آخر إدخال", width="stretch",
                         disabled=not st.session_state.undo_stack)

    if preview:
        parsed = parse_daily_fleet_messages(raw, entry_date.isoformat())
        if not parsed:
            st.warning("لم يتم التعرف على أي سيارة في النص. تأكد من وجود "
                       "عبارة «سيارة رقم ...» أو «شاحنة رقم ...».")
        else:
            st.success(f"تم التعرف على {len(parsed)} سجل (معاينة بدون حفظ).")
            st.dataframe(pd.DataFrame(parsed), width="stretch",
                         hide_index=True)

    if analyze:
        parsed = parse_daily_fleet_messages(raw, entry_date.isoformat())
        if not parsed:
            st.warning("لم يتم التعرف على أي سيارة في النص.")
        else:
            result = add_batch(parsed)
            st.success(f"✅ تم حفظ {result['added']} سجل بنجاح.")
            for alert in result["alerts"]:
                st.error(
                    f"🚨 السيارة {alert['plate']} بلغت حد تغيير الزيت "
                    f"({alert['limit']:,.0f} كم) في الدورة رقم {alert['cycle']}. "
                    "توقف العداد عند الحد ولن يتجاوزه. اعتمد تغيير الزيت من "
                    "لوحة التحكم لتبدأ دورة جديدة من الصفر.")
            st.dataframe(pd.DataFrame(parsed), width="stretch",
                         hide_index=True)

    if undo:
        removed = undo_last_batch()
        if removed:
            st.session_state.flash = ("success",
                                      f"تم التراجع عن آخر إدخال ({removed} سجل).")
            st.rerun()
        else:
            st.info("لا يوجد إدخال يمكن التراجع عنه.")

    st.divider()
    st.subheader("➕ إدخال يدوي سريع")
    with st.form("manual_entry", clear_on_submit=True):
        m1, m2, m3 = st.columns(3)
        with m1:
            plate = st.text_input("رقم السيارة")
            zafat = st.number_input("عدد الزفات", min_value=0, step=1, value=0)
        with m2:
            distance = st.number_input("المسافة المقطوعة (كم)", min_value=0.0,
                                       step=1.0, value=0.0)
            time_taken = st.text_input("الوقت المستغرق", value="غير محدد")
        with m3:
            details = st.text_input("تفاصيل الزفات", value="غير محدد")
            manual_date = st.date_input("التاريخ", value=date.today(),
                                        format="YYYY-MM-DD")
        submitted = st.form_submit_button("حفظ السجل", type="primary",
                                          width="stretch")
    if submitted:
        if not plate.strip():
            st.warning("الرجاء إدخال رقم السيارة.")
        else:
            result = add_batch([{
                "التاريخ": manual_date.isoformat(),
                "رقم السيارة": plate.strip(),
                "عدد الزفات": int(zafat),
                "تفاصيل الزفات": details.strip() or "غير محدد",
                "المسافة المقطوعة (كم)": float(distance),
                "الوقت المستغرق": time_taken.strip() or "غير محدد",
            }])
            msg = "تم حفظ السجل بنجاح."
            for alert in result["alerts"]:
                msg += (f" 🚨 السيارة {alert['plate']} بلغت حد الزيت "
                        f"({alert['limit']:,.0f} كم).")
            st.session_state.flash = ("success", msg)
            st.rerun()

    st.divider()
    st.subheader("🕒 آخر السجلات المدخلة")
    show_table(data.tail(15).iloc[::-1], BASE_COLUMNS)


# ---------------------------------------------------------------------------
# 11) القسم الثالث: السجل الشهري المجدول
# ---------------------------------------------------------------------------
def page_monthly():
    st.markdown(styles.header(
        "📋 السجل الشهري المجدول",
        "تجميع أوتوماتيكي لمسافات وزفات كل شاحنة"),
        unsafe_allow_html=True)

    if len(data) == 0:
        st.info("لا توجد بيانات بعد.")
        return

    months = sorted({str(d)[:7] for d in data["التاريخ"] if re.match(r"\d{4}-\d{2}", str(d))},
                    reverse=True)
    if not months:
        st.info("لا توجد تواريخ صالحة في السجلات.")
        return

    current = date.today().strftime("%Y-%m")
    default_index = months.index(current) if current in months else 0
    month = st.selectbox("اختر الشهر", months, index=default_index)

    subset = data[data["التاريخ"].astype(str).str.startswith(month)]
    if len(subset) == 0:
        st.info("لا توجد سجلات في هذا الشهر.")
        return

    grouped = subset.groupby("رقم السيارة").agg(**{
        "عدد أيام العمل": ("التاريخ", "nunique"),
        "إجمالي الزفات": ("عدد الزفات", "sum"),
        "إجمالي المسافة (كم)": ("المسافة المقطوعة (كم)", "sum"),
        "متوسط المسافة اليومية (كم)": ("المسافة المقطوعة (كم)", "mean"),
        "آخر عداد زيت": ("عداد الزيت الحالي", "last"),
        "حد تغيير الزيت": ("حد تغيير الزيت", "last"),
        "دورة الزيت": ("دورة الزيت", "last"),
    }).reset_index()
    grouped["متوسط المسافة اليومية (كم)"] = grouped["متوسط المسافة اليومية (كم)"].round(1)
    grouped["إجمالي المسافة (كم)"] = grouped["إجمالي المسافة (كم)"].round(1)

    c = st.columns(4)
    totals = [
        ("🚛", grouped["رقم السيارة"].nunique(), "عدد الشاحنات العاملة", "ok"),
        ("🛣️", f'{grouped["إجمالي المسافة (كم)"].sum():,.0f}', "إجمالي المسافة (كم)", "ok"),
        ("🗑️", int(grouped["إجمالي الزفات"].sum()), "إجمالي الزفات", "ok"),
        ("📅", subset["التاريخ"].nunique(), "أيام العمل في الشهر", "ok"),
    ]
    for col, (icon, value, label, tone) in zip(c, totals):
        with col:
            st.markdown(styles.stat_card(icon, value, label, tone),
                        unsafe_allow_html=True)

    st.subheader(f"ملخص شهر {month}")
    show_table(grouped)

    st.subheader("📈 المسافة المقطوعة حسب السيارة")
    st.bar_chart(grouped.set_index("رقم السيارة")["إجمالي المسافة (كم)"])

    st.subheader("🗂️ التفاصيل اليومية للشهر")
    show_table(subset.sort_values("التاريخ"), BASE_COLUMNS)

    st.download_button(
        "⬇️ تنزيل ملخص الشهر (CSV)",
        data=grouped.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"monthly_summary_{month}.csv",
        mime="text/csv",
        width="stretch",
    )


# ---------------------------------------------------------------------------
# 12) القسم الرابع: السجل العام (Excel / CSV)
# ---------------------------------------------------------------------------
def page_export():
    st.markdown(styles.header(
        "📁 السجل العام (Excel / CSV)",
        "أرشيف كامل لكل سجلات الأسطول مع إمكانية التصفية والتنزيل"),
        unsafe_allow_html=True)

    if len(data) == 0:
        st.info("لا توجد بيانات للتصدير.")
        return

    f1, f2, f3 = st.columns(3)
    with f1:
        plates = ["الكل"] + sorted(data["رقم السيارة"].unique().tolist())
        plate = st.selectbox("رقم السيارة", plates)
    with f2:
        start = st.date_input("من تاريخ", value=date.today().replace(day=1),
                              format="YYYY-MM-DD")
    with f3:
        end = st.date_input("إلى تاريخ", value=date.today(), format="YYYY-MM-DD")

    subset = data.copy()
    if plate != "الكل":
        subset = subset[subset["رقم السيارة"] == plate]
    subset = subset[(subset["التاريخ"] >= start.isoformat()) &
                    (subset["التاريخ"] <= end.isoformat())]

    st.caption(f"عدد السجلات المطابقة: **{len(subset)}** — "
               f"إجمالي المسافة: **{subset['المسافة المقطوعة (كم)'].sum():,.0f} كم**")
    show_table(subset.sort_values("التاريخ"), BASE_COLUMNS)

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "⬇️ تنزيل السجلات المطابقة (CSV عربي)",
            data=subset[BASE_COLUMNS].to_csv(index=False).encode("utf-8-sig"),
            file_name=f"fleet_records_{start}_{end}.csv",
            mime="text/csv",
            width="stretch",
        )
    with d2:
        st.download_button(
            "⬇️ تنزيل السجل العام كاملاً (CSV عربي)",
            data=data[BASE_COLUMNS].to_csv(index=False).encode("utf-8-sig"),
            file_name="fleet_records_all.csv",
            mime="text/csv",
            width="stretch",
        )

    st.divider()
    st.subheader("🛢️ سجل تغيير الزيت (الدورات المغلقة)")
    try:
        log = STORAGE.load_oil_log()
    except Exception as exc:  # noqa: BLE001
        log = None
        st.warning(f"تعذر تحميل سجل الزيت: {exc}")
    if log is not None and len(log):
        show_table(log)
        st.download_button(
            "⬇️ تنزيل سجل تغيير الزيت (CSV عربي)",
            data=log.to_csv(index=False).encode("utf-8-sig"),
            file_name="oil_change_log.csv",
            mime="text/csv",
            width="stretch",
        )
    else:
        st.info("لا توجد دورات زيت مغلقة حتى الآن.")


# ---------------------------------------------------------------------------
# 13) القسم الخامس: الإعدادات العامة والصيانة
# ---------------------------------------------------------------------------
def page_settings():
    st.markdown(styles.header(
        "⚙️ الإعدادات العامة والصيانة",
        "التحكم بحد الزيت، الثيم، البيانات، والجلسة"),
        unsafe_allow_html=True)

    # --- إعدادات الزيت ----------------------------------------------------
    st.subheader("🛢️ إعدادات حساب الزيت")
    st.markdown(styles.panel(
        "العداد يبدأ من الصفر ويتجمع حتى يبلغ الحد الذي تحدده أنت، "
        "ثم يتوقف عنده ولا يتجاوزه أبداً. بعد اعتماد تغيير الزيت تُغلق الدورة "
        "وتبدأ دورة جديدة من الصفر، مستقلة تماماً عن سابقتها."),
        unsafe_allow_html=True)

    with st.form("oil_settings"):
        s1, s2 = st.columns(2)
        with s1:
            new_limit = st.number_input(
                "حد تغيير الزيت (كم) — تحدده أنت",
                min_value=100.0, max_value=100000.0, step=100.0,
                value=float(OIL_LIMIT))
        with s2:
            new_factor = st.number_input(
                "معامل احتساب العداد (1 = المسافة كما هي، 2 = المسافة × 2)",
                min_value=0.1, max_value=10.0, step=0.1, value=float(OIL_FACTOR))
        apply_all = st.checkbox(
            "تطبيق الحد الجديد على جميع السيارات في دوراتها الحالية", value=True)
        saved = st.form_submit_button("💾 حفظ الإعدادات", type="primary",
                                      width="stretch")
    if saved:
        st.session_state.settings["oil_limit"] = float(new_limit)
        st.session_state.settings["oil_factor"] = float(new_factor)
        STORAGE.save_settings({
            "oil_limit": str(new_limit),
            "oil_factor": str(new_factor),
        })
        if apply_all:
            mapping = state_map()
            for state in mapping.values():
                state["حد تغيير الزيت"] = float(new_limit)
                state["عداد الدورة"] = min(float(state["عداد الدورة"]),
                                           float(new_limit))
            save_state_map(mapping)
        st.session_state.flash = ("success", "تم حفظ الإعدادات بنجاح.")
        st.rerun()

    # --- إغلاق دورة يدوياً -------------------------------------------------
    st.subheader("🔄 اعتماد تغيير الزيت (بدء دورة جديدة)")
    overview = fleet_overview()
    if len(overview):
        r1, r2 = st.columns([3, 1])
        with r1:
            target = st.selectbox("اختر السيارة",
                                  overview["رقم السيارة"].tolist())
        with r2:
            st.write("")
            if st.button("✅ إغلاق الدورة", width="stretch"):
                close_cycle(str(target))
                st.session_state.flash = (
                    "success",
                    f"تم إغلاق دورة السيارة {target} وبدء دورة جديدة من الصفر.")
                st.rerun()
        show_table(overview)
    else:
        st.info("لا توجد سيارات مسجلة بعد.")

    # --- الثيم -------------------------------------------------------------
    st.subheader("🎨 الوضع النهاري والداكن")
    st.markdown(styles.panel(
        "لتغيير الثيم: اضغط على قائمة الثلاث نقاط (⋮) أعلى يمين الشاشة ← "
        "<b>Settings</b> ← اختر <b>Light</b> أو <b>Dark</b>. "
        "يتكيّف التطبيق بالكامل فوراً لأنه يعتمد على متغيرات ثيم ستريملت الأصلية."),
        unsafe_allow_html=True)

    # --- معلومات النظام ----------------------------------------------------
    st.subheader("ℹ️ معلومات النظام")
    info = STORAGE.info()
    st.markdown(styles.panel(
        f"<b>الجهة:</b> {ORG_NAME}<br>"
        f"<b>إصدار التطبيق:</b> {APP_VERSION}<br>"
        f"<b>محرك التخزين:</b> {info['label']}<br>"
        f"<b>موقع البيانات:</b> {info['location']}<br>"
        f"<b>حالة الاتصال:</b> {STORAGE_MSG}<br>"
        f"<b>إجمالي السجلات:</b> {len(data)}"),
        unsafe_allow_html=True)
    if info.get("url"):
        st.link_button("🔗 فتح جدول البيانات في Google Sheets", info["url"],
                       width="stretch")
    if st.button("🔄 تحديث البيانات من قاعدة البيانات", width="stretch"):
        reload_from_storage()
        st.session_state.flash = ("success", "تم تحديث البيانات.")
        st.rerun()

    # --- منطقة الحذف المتقدمة ---------------------------------------------
    st.subheader("🗑️ منطقة الحذف المتقدمة")
    st.warning("تنبيه: عمليات الحذف نهائية ولا يمكن التراجع عنها.")

    if len(data) == 0:
        st.info("لا توجد بيانات قابلة للحذف.")
    else:
        t1, t2 = st.tabs(["حذف سجل سيارة لتاريخ محدد", "حذف كافة بيانات يوم كامل"])

        with t1:
            c1, c2 = st.columns(2)
            with c1:
                del_plate = st.selectbox(
                    "رقم السيارة", sorted(data["رقم السيارة"].unique().tolist()),
                    key="del_plate")
            with c2:
                plate_dates = sorted(
                    data[data["رقم السيارة"] == del_plate]["التاريخ"].unique().tolist(),
                    reverse=True)
                del_date = st.selectbox("التاريخ", plate_dates, key="del_date")
            confirm1 = st.checkbox("أؤكد حذف هذا السجل", key="c1")
            if st.button("حذف السجل المحدد", type="primary",
                         width="stretch", disabled=not confirm1):
                mask = ((data["رقم السيارة"] == del_plate) &
                        (data["التاريخ"] == del_date))
                removed = delete_records(mask)
                st.session_state.flash = (
                    "success", f"تم حذف {removed} سجل للسيارة {del_plate} "
                               f"بتاريخ {del_date}.")
                st.rerun()

        with t2:
            all_dates = sorted(data["التاريخ"].unique().tolist(), reverse=True)
            day = st.selectbox("اختر اليوم", all_dates, key="del_day")
            count = int((data["التاريخ"] == day).sum())
            st.caption(f"عدد السجلات في هذا اليوم: **{count}**")
            confirm2 = st.checkbox("أؤكد حذف كافة سجلات هذا اليوم", key="c2")
            if st.button("حذف بيانات اليوم كاملاً", type="primary",
                         width="stretch", disabled=not confirm2):
                removed = delete_records(data["التاريخ"] == day)
                st.session_state.flash = (
                    "success", f"تم حذف {removed} سجل بتاريخ {day}.")
                st.rerun()

    # --- تسجيل الخروج ------------------------------------------------------
    st.subheader("🚪 الجلسة")
    if st.button("تسجيل الخروج الآمن", width="stretch"):
        st.session_state.logged_in = False
        st.rerun()


# ---------------------------------------------------------------------------
# 14) التوجيه
# ---------------------------------------------------------------------------
PAGES = {
    SECTIONS[0]: page_dashboard,
    SECTIONS[1]: page_daily,
    SECTIONS[2]: page_monthly,
    SECTIONS[3]: page_export,
    SECTIONS[4]: page_settings,
}
PAGES[section]()

st.caption(f"{APP_ICON} {ORG_NAME} — الإصدار {APP_VERSION}")
