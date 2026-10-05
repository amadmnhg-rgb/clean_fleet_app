# -*- coding: utf-8 -*-
"""
طبقة التخزين.

  * SheetsStorage : تخزين سحابي على Google Sheets — ينشئ جدول البيانات
                    وكل أوراقه تلقائياً من داخل التطبيق دون أي عمل يدوي.
  * LocalStorage  : تخزين محلي بملفات CSV يعمل تلقائياً عند عدم توفر
                    بيانات اعتماد Google، حتى يبقى التطبيق قابلاً للتشغيل دائماً.

كلا المحركين يوفران نفس الواجهة البرمجية تماماً.
"""

from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime

import pandas as pd

from .config import (
    ALL_COLUMNS,
    DEFAULT_OIL_FACTOR,
    DEFAULT_OIL_LIMIT,
    DEFAULT_SETTINGS,
    LOCAL_DATA_DIR,
    NUMERIC_COLUMNS,
    OIL_LOG_COLUMNS,
    OIL_STATE_COLUMNS,
    SETTINGS_COLUMNS,
    SPREADSHEET_TITLE,
    WS_OIL_LOG,
    WS_OIL_STATE,
    WS_RECORDS,
    WS_SETTINGS,
)
from .oil import add_distance

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# أدوات مشتركة
# ---------------------------------------------------------------------------
def normalize_sheet_rows(rows: list, width: int) -> list:
    """
    يوحّد طول كل صف من صفوف Google Sheets ليطابق عدد أعمدة صف العناوين
    تماماً (حشو بالفراغ إن كان أقصر، أو قصّ إن كان أطول).

    Google Sheets API يحذف أحياناً الخلايا الفارغة الزائدة في نهاية الصف
    عند إرجاع get_all_values()، فتأتي بعض الصفوف (خصوصاً القديمة منها، أو
    التي كُتبت قبل إضافة أعمدة جديدة لاحقاً للمخطط) أقصر من صف العناوين
    الحالي. بدون هذه الحماية يرفض pandas.DataFrame البيانات بالكامل
    (ValueError) فيظهر الجدول فارغاً وكأن البيانات اختفت، رغم أنها ما
    زالت موجودة فعلياً في الشيت نفسه.
    """
    normalized = []
    for row in rows:
        if len(row) < width:
            row = list(row) + [""] * (width - len(row))
        elif len(row) > width:
            row = list(row)[:width]
        normalized.append(row)
    return normalized


def empty_records_df() -> pd.DataFrame:
    return pd.DataFrame(columns=ALL_COLUMNS)


def coerce_records(df: pd.DataFrame) -> pd.DataFrame:
    """ضبط الأعمدة والأنواع لجدول السجلات."""
    if df is None or len(df) == 0:
        return empty_records_df()
    df = df.copy()
    for col in ALL_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col not in NUMERIC_COLUMNS else 0
    df = df[ALL_COLUMNS]
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in ["التاريخ", "رقم السيارة", "تفاصيل الزفات", "الوقت المستغرق",
                "معرف السجل", "رقم الدفعة"]:
        df[col] = df[col].astype(str).str.strip()
    df["عدد الزفات"] = df["عدد الزفات"].astype(int)
    return df.reset_index(drop=True)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# التخزين المحلي (CSV)
# ---------------------------------------------------------------------------
class LocalStorage:
    backend = "local"
    label = "تخزين محلي (ملفات CSV)"

    def __init__(self, data_dir: str = LOCAL_DATA_DIR):
        self.dir = data_dir
        os.makedirs(self.dir, exist_ok=True)
        self.files = {
            WS_RECORDS: os.path.join(self.dir, "records.csv"),
            WS_OIL_STATE: os.path.join(self.dir, "oil_state.csv"),
            WS_OIL_LOG: os.path.join(self.dir, "oil_log.csv"),
            WS_SETTINGS: os.path.join(self.dir, "settings.csv"),
        }
        self._bootstrap()

    # -- داخلي -------------------------------------------------------------
    def _bootstrap(self):
        defaults = {
            WS_RECORDS: ALL_COLUMNS,
            WS_OIL_STATE: OIL_STATE_COLUMNS,
            WS_OIL_LOG: OIL_LOG_COLUMNS,
            WS_SETTINGS: SETTINGS_COLUMNS,
        }
        for key, columns in defaults.items():
            path = self.files[key]
            if not os.path.exists(path):
                pd.DataFrame(columns=columns).to_csv(
                    path, index=False, encoding="utf-8-sig")
        if self.load_settings() == {}:
            self.save_settings(DEFAULT_SETTINGS)

    def _read(self, key: str, columns: list) -> pd.DataFrame:
        path = self.files[key]
        if not os.path.exists(path):
            return pd.DataFrame(columns=columns)
        try:
            df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=columns)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df[columns]

    def _write(self, key: str, df: pd.DataFrame, columns: list):
        df = df.copy()
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        df[columns].to_csv(self.files[key], index=False, encoding="utf-8-sig")

    # -- السجلات ------------------------------------------------------------
    def load_records(self) -> pd.DataFrame:
        return coerce_records(self._read(WS_RECORDS, ALL_COLUMNS))

    def save_records(self, df: pd.DataFrame):
        self._write(WS_RECORDS, coerce_records(df), ALL_COLUMNS)

    def append_records(self, rows: list):
        with _LOCK:
            current = self.load_records()
            new = coerce_records(pd.DataFrame(rows))
            self.save_records(pd.concat([current, new], ignore_index=True))

    # -- حالة الزيت ---------------------------------------------------------
    def load_oil_state(self) -> pd.DataFrame:
        return self._read(WS_OIL_STATE, OIL_STATE_COLUMNS)

    def save_oil_state(self, df: pd.DataFrame):
        self._write(WS_OIL_STATE, df, OIL_STATE_COLUMNS)

    # -- سجل تغيير الزيت ----------------------------------------------------
    def load_oil_log(self) -> pd.DataFrame:
        return self._read(WS_OIL_LOG, OIL_LOG_COLUMNS)

    def append_oil_log(self, row: dict):
        with _LOCK:
            df = self.load_oil_log()
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            self._write(WS_OIL_LOG, df, OIL_LOG_COLUMNS)

    # -- الإعدادات ----------------------------------------------------------
    def load_settings(self) -> dict:
        df = self._read(WS_SETTINGS, SETTINGS_COLUMNS)
        return {str(k): str(v) for k, v in zip(df["المفتاح"], df["القيمة"]) if str(k).strip()}

    def save_settings(self, settings: dict):
        df = pd.DataFrame(
            [{"المفتاح": k, "القيمة": str(v)} for k, v in settings.items()])
        self._write(WS_SETTINGS, df, SETTINGS_COLUMNS)

    # -- معلومات ------------------------------------------------------------
    def info(self) -> dict:
        return {
            "backend": self.backend,
            "label": self.label,
            "location": os.path.abspath(self.dir),
            "url": "",
        }


# ---------------------------------------------------------------------------
# التخزين السحابي (Google Sheets)
# ---------------------------------------------------------------------------
class SheetsStorage:
    backend = "gsheets"
    label = "Google Sheets (سحابي)"

    def __init__(self, credentials: dict, title: str = SPREADSHEET_TITLE,
                 spreadsheet_id: str = "", share_with: list = None):
        import gspread  # يُستورد هنا حتى لا يكون إلزامياً في الوضع المحلي

        self._gspread = gspread
        self.client = gspread.service_account_from_dict(
            credentials, scopes=GOOGLE_SCOPES)
        self.title = title or SPREADSHEET_TITLE
        self.share_with = [e for e in (share_with or []) if e]
        self.sh = self._open_or_create(spreadsheet_id)
        self._ensure_worksheets()

    # -- التهيئة التلقائية --------------------------------------------------
    def _open_or_create(self, spreadsheet_id: str = ""):
        gspread = self._gspread
        if spreadsheet_id:
            return self.client.open_by_key(spreadsheet_id)
        try:
            return self.client.open(self.title)
        except gspread.SpreadsheetNotFound:
            sh = self.client.create(self.title)
            for email in self.share_with:
                try:
                    sh.share(email, perm_type="user", role="writer",
                             notify=False)
                except Exception:
                    pass
            return sh

    def _ensure_worksheets(self):
        wanted = {
            WS_RECORDS: ALL_COLUMNS,
            WS_OIL_STATE: OIL_STATE_COLUMNS,
            WS_OIL_LOG: OIL_LOG_COLUMNS,
            WS_SETTINGS: SETTINGS_COLUMNS,
        }
        existing = {ws.title: ws for ws in self.sh.worksheets()}
        for name, columns in wanted.items():
            if name in existing:
                ws = existing[name]
                header = [h.strip() for h in ws.row_values(1)]
                missing = [c for c in columns if c not in header]
                if missing:
                    # نُلحق الأعمدة الناقصة فقط في نهاية الصف الأول، ولا
                    # نستبدل صف العناوين بالكامل أبداً: استبداله بالكامل
                    # قد يُعيد ترتيب الأعمدة بينما تبقى بيانات الصفوف
                    # القديمة بترتيبها الفعلي القديم، فتنزاح كل قيمة إلى
                    # عمود غير صحيح. هذا كان سبباً حقيقياً محتملاً لفقدان
                    # البيانات ظاهرياً بعد تحديثات المخطط السابقة.
                    ws.update(values=[header + missing], range_name="A1")
            else:
                ws = self.sh.add_worksheet(
                    title=name, rows=2000, cols=max(10, len(columns)))
                ws.update(values=[columns], range_name="A1")
        # حذف الورقة الافتراضية الفارغة إن وُجدت
        for title in ("Sheet1", "ورقة1"):
            if title in existing and title not in wanted:
                try:
                    self.sh.del_worksheet(existing[title])
                except Exception:
                    pass
        if not self.load_settings():
            self.save_settings(DEFAULT_SETTINGS)

    def _ws(self, name: str):
        return self.sh.worksheet(name)

    def _read(self, name: str, columns: list) -> pd.DataFrame:
        values = self._ws(name).get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=columns)
        header = [h.strip() for h in values[0]]
        rows = normalize_sheet_rows(values[1:], len(header))
        df = pd.DataFrame(rows, columns=header)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df[columns].fillna("")

    def _write(self, name: str, df: pd.DataFrame, columns: list):
        df = df.copy()
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        body = [columns] + df[columns].astype(str).values.tolist()
        ws = self._ws(name)
        ws.clear()
        ws.update(values=body, range_name="A1", value_input_option="USER_ENTERED")

    # -- السجلات ------------------------------------------------------------
    def load_records(self) -> pd.DataFrame:
        return coerce_records(self._read(WS_RECORDS, ALL_COLUMNS))

    def save_records(self, df: pd.DataFrame):
        self._write(WS_RECORDS, coerce_records(df), ALL_COLUMNS)

    def append_records(self, rows: list):
        with _LOCK:
            df = coerce_records(pd.DataFrame(rows))
            body = df[ALL_COLUMNS].astype(str).values.tolist()
            self._ws(WS_RECORDS).append_rows(
                body, value_input_option="USER_ENTERED")

    # -- حالة الزيت ---------------------------------------------------------
    def load_oil_state(self) -> pd.DataFrame:
        return self._read(WS_OIL_STATE, OIL_STATE_COLUMNS)

    def save_oil_state(self, df: pd.DataFrame):
        self._write(WS_OIL_STATE, df, OIL_STATE_COLUMNS)

    # -- سجل تغيير الزيت ----------------------------------------------------
    def load_oil_log(self) -> pd.DataFrame:
        return self._read(WS_OIL_LOG, OIL_LOG_COLUMNS)

    def append_oil_log(self, row: dict):
        values = [[str(row.get(c, "")) for c in OIL_LOG_COLUMNS]]
        self._ws(WS_OIL_LOG).append_rows(
            values, value_input_option="USER_ENTERED")

    # -- الإعدادات ----------------------------------------------------------
    def load_settings(self) -> dict:
        df = self._read(WS_SETTINGS, SETTINGS_COLUMNS)
        return {str(k): str(v) for k, v in zip(df["المفتاح"], df["القيمة"])
                if str(k).strip()}

    def save_settings(self, settings: dict):
        df = pd.DataFrame(
            [{"المفتاح": k, "القيمة": str(v)} for k, v in settings.items()])
        self._write(WS_SETTINGS, df, SETTINGS_COLUMNS)

    # -- معلومات ------------------------------------------------------------
    def info(self) -> dict:
        return {
            "backend": self.backend,
            "label": self.label,
            "location": self.sh.title,
            "url": getattr(self.sh, "url", ""),
        }


# ---------------------------------------------------------------------------
# المُنشئ الذكي
# ---------------------------------------------------------------------------
def build_storage(secrets: dict = None, allow_local_fallback: bool = False):
    """
    يحاول الاتصال بـ Google Sheets باستخدام بيانات الاعتماد في st.secrets.

    التخزين المحلي (CSV) غير معتمد للتشغيل الفعلي بعد الآن: أي ملف محلي
    يُكتب على خادم Streamlit Cloud يُفقَد عند أي Reboot أو خمول للسيرفر
    (القرص المحلي هناك غير دائم أصلاً)، وهذا هو السبب الحقيقي وراء
    "اختفاء البيانات" — وليس خللاً في منطق الحفظ نفسه. لذلك، افتراضياً
    (allow_local_fallback=False) لا يعود هذا المُنشئ للتخزين المحلي
    صامتاً أبداً: إن تعذّر الاتصال الحقيقي بـ Google Sheets يُرجع
    is_cloud=False (مع storage=None)، ليوقف app.py التطبيق بشاشة إعداد
    واضحة بدل تشغيله بصمت على تخزين مؤقت يضيع لاحقاً.

    الاستثناء الوحيد: allow_local_fallback=True صراحةً — مخصص فقط للتطوير
    المحلي ومجموعة الاختبارات الآلية عبر متغيّر البيئة
    FLEET_ALLOW_LOCAL_STORAGE الذي يفعّله app.py لوحده، وليس للنشر الفعلي
    على Streamlit Cloud.

    يُرجع: (كائن التخزين (أو None إن فشل بلا سماح بالتخزين المحلي),
            رسالة الحالة, هل الاتصال سحابي ناجح؟). عندما يكون العنصر
            الثالث False وallow_local_fallback=False، يتوقع المستدعي أن
            يستدعي st.stop() ولا يعتدّ بعنصر التخزين إطلاقاً.
    """
    secrets = secrets or {}
    creds = secrets.get("gcp_service_account")

    if not creds:
        msg = "لم يتم العثور على بيانات اعتماد Google (gcp_service_account) في إعدادات Secrets."
        if allow_local_fallback:
            return LocalStorage(), msg + " تم تفعيل التخزين المحلي (وضع تطوير محلي فقط).", False
        return None, msg, False

    try:
        creds = dict(creds)
        if "private_key" in creds:
            creds["private_key"] = str(creds["private_key"]).replace("\\n", "\n")
        gs_conf = dict(secrets.get("gsheets", {}) or {})
        share_with = gs_conf.get("share_with", [])
        if isinstance(share_with, str):
            share_with = [e.strip() for e in share_with.split(",") if e.strip()]
        storage = SheetsStorage(
            credentials=creds,
            title=gs_conf.get("spreadsheet_title", SPREADSHEET_TITLE),
            spreadsheet_id=gs_conf.get("spreadsheet_id", ""),
            share_with=share_with,
        )
        msg = "تم الاتصال بـ Google Sheets بنجاح — كل القراءة والكتابة دائمة ولحظية."
        if not gs_conf.get("spreadsheet_id"):
            msg += (" تنبيه: لم يُحدَّد spreadsheet_id ثابت في Secrets؛ يُفضَّل "
                   "تثبيته بعد إنشاء الجدول أول مرة لضمان العثور عليه نفسه "
                   "دائماً بدل البحث عنه بالاسم في كل مرة.")
        return storage, msg, True
    except Exception as exc:  # noqa: BLE001
        msg = f"بيانات الاعتماد موجودة لكن تعذّر الاتصال الفعلي بـ Google Sheets: {exc}"
        if allow_local_fallback:
            return LocalStorage(), msg + " تم تفعيل التخزين المحلي (وضع تطوير محلي فقط).", False
        return None, msg, False


# ---------------------------------------------------------------------------
# واجهة الوحدة (Module API) — ما تستدعيه app.py مباشرة
#
# تُجمّع هذه الدوال عمل المخزن خلف واجهة واحدة ثابتة (load_data / add_records
# / close_oil_cycle ...) حتى تعمل app.py بلا AttributeErrors مهما كان المخزن
# المفعّل (Google Sheets أو المحلي) خلف الكواليس.
# ---------------------------------------------------------------------------

_STORE = None
_STORE_MSG = ""
_STORE_CLOUD = False


def _env_allows_local() -> bool:
    return os.getenv("FLEET_ALLOW_LOCAL_STORAGE", "").strip().lower() in (
        "1", "true", "yes")


def init_storage(allow_local_fallback: bool = None):
    """
    يبني (أو يُعيد استخدام) مخزن البيانات ويُرجع: (المخزن, رسالة الحالة, سحابي؟).

    يقرأ بيانات اعتماد Google من st.secrets إن وُجدت، ولا يعود للتخزين المحلي
    إلا عند السماح صراحةً (allow_local_fallback=True أو متغيّر البيئة
    FLEET_ALLOW_LOCAL_STORAGE=1) — بوابة الحماية نفسها التي يوثقها README
    حمايةً لبيانات الإنتاج من الضياع عند إعادة التشغيل.
    """
    global _STORE, _STORE_MSG, _STORE_CLOUD
    if _STORE is not None:
        return _STORE, _STORE_MSG, _STORE_CLOUD
    if allow_local_fallback is None:
        allow_local_fallback = _env_allows_local()

    secrets = {}
    try:
        import streamlit as st
        secrets = {key: st.secrets[key] for key in st.secrets.keys()}
    except Exception:
        # لا توجد ملف secrets (تطوير محلي/اختبارات) — تُعامل كغياب بيانات اعتماد
        secrets = {}

    with _LOCK:
        if _STORE is None:
            store, msg, is_cloud = build_storage(
                secrets=secrets, allow_local_fallback=bool(allow_local_fallback))
            _STORE, _STORE_MSG, _STORE_CLOUD = store, msg, is_cloud
    return _STORE, _STORE_MSG, _STORE_CLOUD


def _require_store():
    store, _, _ = init_storage()
    if store is None:
        raise RuntimeError(
            "لا يوجد مخزن بيانات متاح: أضف بيانات اعتماد Google "
            "(gcp_service_account) في Secrets أو فعّل FLEET_ALLOW_LOCAL_STORAGE=1 "
            "للتطوير المحلي.")
    return store


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return float(str(value).strip() or default)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int = 0) -> int:
    return int(_to_float(value, float(default)))


def _state_rows(store) -> dict:
    """يقرأ عدادات دورات الزيت كقاموس {رقم السيارة: قيم العداد}."""
    df = store.load_oil_state()
    states = {}
    if df is None or len(df) == 0:
        return states
    for _, row in df.iterrows():
        plate = str(row.get("رقم السيارة", "") or "").strip()
        if not plate:
            continue
        states[plate] = {
            "دورة الزيت": _to_int(row.get("دورة الزيت"), 1) or 1,
            "عداد الدورة": _to_float(row.get("عداد الدورة"), 0.0),
            "حد تغيير الزيت": _to_float(row.get("حد تغيير الزيت"), 0.0),
            "تاريخ بداية الدورة": str(row.get("تاريخ بداية الدورة", "") or ""),
            "آخر تحديث": str(row.get("آخر تحديث", "") or ""),
        }
    return states


def _save_states(store, states: dict):
    rows = [{
        "رقم السيارة": plate,
        "دورة الزيت": int(values.get("دورة الزيت", 1) or 1),
        "عداد الدورة": round(_to_float(values.get("عداد الدورة"), 0.0), 2),
        "حد تغيير الزيت": round(_to_float(values.get("حد تغيير الزيت"), 0.0), 2),
        "تاريخ بداية الدورة": values.get("تاريخ بداية الدورة", ""),
        "آخر تحديث": values.get("آخر تحديث", "") or _now(),
    } for plate, values in sorted(states.items())]
    store.save_oil_state(pd.DataFrame(rows, columns=OIL_STATE_COLUMNS))


def _fingerprint(row: dict) -> tuple:
    """بصمة السجل لمنع تكرار نفس الصف عند طلب dedup."""
    return (
        str(row.get("التاريخ", "") or "").strip()[:10],
        str(row.get("رقم السيارة", "") or "").strip(),
        str(row.get("عدد الزفات", "") or "").strip(),
        round(_to_float(row.get("المسافة المقطوعة (كم)"), 0.0), 2),
        str(row.get("تفاصيل الزفات", "") or "").strip(),
        str(row.get("الوقت المستغرق", "") or "").strip(),
    )


def load_data(force_reload: bool = False) -> pd.DataFrame:
    """
    يجلب جميع سجلات الحركة — الدالة التي تستدعيها app.py عند بدء التشغيل
    وبعد كل عملية حفظ/تحديث (force_reload للتوافق مع استدعاءات app.py؛
    القراءة حديثة أصلاً من المخزن المفعّل).
    """
    del force_reload  # القراءة تتم دائماً مباشرة من المخزن (لا كاش وسيط)
    return _require_store().load_records()


def load_settings() -> dict:
    """الإعدادات بقيم رقمية جاهزة للاستعمال المباشر (oil_limit / oil_factor)."""
    raw = _require_store().load_settings() or {}
    settings = dict(raw)
    try:
        settings["oil_limit"] = float(settings.get("oil_limit"))
    except (TypeError, ValueError):
        settings["oil_limit"] = float(DEFAULT_OIL_LIMIT)
    try:
        settings["oil_factor"] = float(settings.get("oil_factor"))
    except (TypeError, ValueError):
        settings["oil_factor"] = float(DEFAULT_OIL_FACTOR)
    return settings


def save_settings(settings: dict):
    """يحفظ الإعدادات كما هي (تُحوَّل القيم إلى نص عند الكتابة)."""
    if not isinstance(settings, dict):
        raise TypeError("الإعدادات يجب أن تكون قاموساً من المفاتيح والقيم.")
    _require_store().save_settings(settings)


def load_oil_state() -> pd.DataFrame:
    """عدادات دورات الزيت الحالية لكل سيارة."""
    return _require_store().load_oil_state()


def load_oil_logs() -> pd.DataFrame:
    """سجل تغييرات الزيت المكتملة (يدور حوله تاريخ الاستحقاق في app.py)."""
    return _require_store().load_oil_log()


def add_records(rows: list, dedup: bool = False) -> dict:
    """
    يضيف سجلات حركة جديدة، ويحدّث عدادات دورات الزيت تبعاً لها، ويعيد
    dict يحوي مفتاح error (None عند النجاح) — عقد app.py: res.get("error").

    عند dedup=True تُرفض السجلات المطابقة لبصمة موجودة. السجلات تُثبّت
    أعمدة العداد (عداد الزيت الحالي / حد تغيير الزيت / دورة الزيت) وقت
    الحفظ، والعداد لا يتجاوز الحد أبداً (oil.add_distance).
    """
    try:
        if not rows:
            return {"added": 0, "duplicates": 0, "reached_limit": [],
                    "batch_id": "", "error": None}
        store = _require_store()
        settings = load_settings()
        limit = max(1.0, float(settings.get("oil_limit", DEFAULT_OIL_LIMIT)))
        factor = float(settings.get("oil_factor", DEFAULT_OIL_FACTOR))

        existing_fps = set()
        if dedup:
            try:
                existing_fps = {
                    _fingerprint(record)
                    for _, record in store.load_records().iterrows()
                }
            except Exception:
                existing_fps = set()

        states = _state_rows(store)
        batch_id = uuid.uuid4().hex
        prepared, seen = [], set()
        duplicates, reached = 0, []

        for raw in rows:
            if not isinstance(raw, dict):
                return {"error": "كل سجل يجب أن يكون قاموساً بأعمدته المطلوبة."}
            row = dict(raw)
            plate = str(row.get("رقم السيارة", "") or "").strip()
            if not plate or plate.lower() in ("nan", "none"):
                return {"error": "رقم السيارة مفقود في أحد السجلات المراد حفظها."}
            row["رقم السيارة"] = plate
            row_date = str(row.get("التاريخ", "") or "").strip()[:10]
            row["التاريخ"] = row_date or datetime.now().date().isoformat()
            km = round(max(0.0, _to_float(row.get("المسافة المقطوعة (كم)"), 0.0)), 2)
            row["المسافة المقطوعة (كم)"] = km

            fp = _fingerprint(row)
            if dedup and (fp in existing_fps or fp in seen):
                duplicates += 1
                continue
            seen.add(fp)

            state = states.get(plate)
            if state is None:
                state = {
                    "دورة الزيت": 1,
                    "عداد الدورة": 0.0,
                    "حد تغيير الزيت": 0.0,
                    "تاريخ بداية الدورة": row["التاريخ"],
                    "آخر تحديث": "",
                }
                states[plate] = state
            state_limit = _to_float(state.get("حد تغيير الزيت"), 0.0) or limit
            new_counter, hit, _dropped = add_distance(
                _to_float(state.get("عداد الدورة"), 0.0),
                state_limit, km, factor)
            state["عداد الدورة"] = new_counter
            state["حد تغيير الزيت"] = state_limit
            state["آخر تحديث"] = _now()
            if not state.get("تاريخ بداية الدورة"):
                state["تاريخ بداية الدورة"] = row["التاريخ"]

            row["عداد الزيت الحالي"] = new_counter
            row["حد تغيير الزيت"] = state_limit
            row["دورة الزيت"] = int(_to_int(state.get("دورة الزيت"), 1) or 1)
            if not str(row.get("معرف السجل", "") or "").strip():
                row["معرف السجل"] = uuid.uuid4().hex
            if not str(row.get("رقم الدفعة", "") or "").strip():
                row["رقم الدفعة"] = batch_id

            if hit and plate not in reached:
                reached.append(plate)
            prepared.append(row)

        if prepared:
            store.append_records(prepared)
            _save_states(store, states)
        return {"added": len(prepared), "duplicates": duplicates,
                "reached_limit": reached, "batch_id": batch_id, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def close_oil_cycle(plate_no, close_date=None, note: str = "", limit=None) -> dict:
    """
    يغلق دورة زيت سيارة: قيد في سجل التغيير + تصفير العداد وبدء دورة جديدة
    (لا يُرحَّل أي فائض — تماماً كقواعد محرك fleet.oil).
    """
    try:
        store = _require_store()
        plate = str(plate_no or "").strip()
        if not plate:
            return {"error": "رقم السيارة مطلوب لإغلاق الدورة."}
        settings = load_settings()
        adopted = _to_float(limit, 0.0) or max(
            1.0, float(settings.get("oil_limit", DEFAULT_OIL_LIMIT)))
        close_date = str(close_date or datetime.now().date().isoformat())[:10]

        states = _state_rows(store)
        state = states.get(plate, {})
        finished_cycle = _to_int(state.get("دورة الزيت"), 1) or 1
        counter = round(_to_float(state.get("عداد الدورة"), 0.0), 2)

        store.append_oil_log({
            "التاريخ": close_date,
            "الوقت": datetime.now().strftime("%H:%M:%S"),
            "رقم السيارة": plate,
            "الدورة المنتهية": finished_cycle,
            "العداد عند الإغلاق": counter,
            "الحد المعتمد": round(adopted, 2),
            "ملاحظة": str(note or ""),
        })
        states[plate] = {
            "دورة الزيت": finished_cycle + 1,
            "عداد الدورة": 0.0,
            "حد تغيير الزيت": adopted,
            "تاريخ بداية الدورة": close_date,
            "آخر تحديث": _now(),
        }
        _save_states(store, states)
        return {"ok": True, "closed_cycle": finished_cycle,
                "new_cycle": finished_cycle + 1, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
