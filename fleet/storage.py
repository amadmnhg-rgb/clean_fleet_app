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
from datetime import datetime

import pandas as pd

from .config import (
    ALL_COLUMNS,
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

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# أدوات مشتركة
# ---------------------------------------------------------------------------
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
                header = ws.row_values(1)
                if [h.strip() for h in header] != columns:
                    ws.update(values=[columns], range_name="A1")
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
        df = pd.DataFrame(values[1:], columns=header)
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
def build_storage(secrets: dict = None):
    """
    يحاول الاتصال بـ Google Sheets باستخدام بيانات الاعتماد في st.secrets،
    وإن لم تتوفر أو فشل الاتصال يعود تلقائياً للتخزين المحلي.

    يُرجع: (كائن التخزين, رسالة الحالة, هل الاتصال سحابي؟)
    """
    secrets = secrets or {}
    creds = secrets.get("gcp_service_account")
    if not creds:
        return LocalStorage(), "لم يتم العثور على بيانات اعتماد Google — تم تفعيل التخزين المحلي.", False
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
        return storage, "تم الاتصال بـ Google Sheets بنجاح.", True
    except Exception as exc:  # noqa: BLE001
        return LocalStorage(), f"تعذر الاتصال بـ Google Sheets ({exc}) — تم تفعيل التخزين المحلي.", False
