# -*- coding: utf-8 -*-
"""
التصميم البصري للتطبيق:
  * خط Cairo من Google Fonts على كل عناصر الواجهة.
  * أسلوب Glassmorphism (زجاج ضبابي + حدود شفافة + ظلال ثلاثية الأبعاد).
  * اعتماد حصري على متغيرات ثيم ستريملت الأصلية ليتبدّل الوضع
    النهاري/الداكن فوراً من قائمة الإعدادات (الثلاث نقاط ← Settings).
  * تجاوب كامل مع شاشات الجوال.
"""

import pandas as pd

from . import util

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap');

/* ---------- الخط العام ---------- */
html, body, .stApp, [class*="css"],
[data-testid="stSidebar"], [data-testid="stMarkdownContainer"],
input, textarea, select, button, .stButton button {
    font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif !important;
}

/* ---------- الاتجاه من اليمين لليسار ---------- */
.stApp { direction: rtl; }
[data-testid="stSidebar"] { direction: rtl; }
[data-testid="stMarkdownContainer"] { text-align: right; }
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    direction: rtl; text-align: right;
}
[data-testid="stDataFrame"] { direction: ltr; }

/* ---------- الألوان من متغيرات ثيم ستريملت (تبديل فوري) ---------- */
.stApp {
    background-color: var(--background-color);
    color: var(--text-color);
}
[data-testid="stSidebar"] > div:first-child {
    background-color: var(--secondary-background-color);
    color: var(--text-color);
    border-inline-start: 1px solid rgba(128,128,128,0.18);
}
[data-testid="stSidebar"] *, [data-testid="stMetricValue"],
[data-testid="stMetricLabel"], h1, h2, h3, h4, h5, h6, p, li, label, span {
    color: var(--text-color);
}

/* ---------- إخفاء واجهة ستريملت الافتراضية بالكامل ----------
   القائمة الجانبية الافتراضية غير مستخدمة إطلاقاً في هذا التطبيق (التنقل
   بالكامل عبر الشريط العائم الموحّد أدناه)، وكذلك أي عناصر تحكم إدارية
   افتراضية (القائمة الثلاثية، شريط الأدوات العلوي، زر Deploy/Manage app
   الأسود) تُخفى جميعها لتبقى الشاشة نظيفة ومخصصة للمستخدم فقط. */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] { display: none !important; }

#MainMenu,
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton,
.stAppDeployButton,
[data-testid="stAppDeployButton"],
[data-testid="manage-app-button"] { display: none !important; visibility: hidden !important; }

.block-container { padding-top: 1.6rem !important; }

[data-testid="stDataFrame"] {
    background-color: var(--secondary-background-color);
    border-radius: 16px;
    padding: 4px;
    border: 1px solid rgba(128,128,128,0.20);
}

/* ---------- ترويسة التطبيق ---------- */
.app-header {
    background: linear-gradient(135deg,
        color-mix(in srgb, var(--primary-color, #1f6feb) 22%, transparent),
        color-mix(in srgb, var(--secondary-background-color) 70%, transparent));
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 22px;
    padding: 18px 22px;
    margin-bottom: 18px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.18);
}
.app-header h1 {
    margin: 0; font-size: 1.5rem; font-weight: 900;
    color: var(--text-color);
}
.app-header p {
    margin: 6px 0 0; opacity: .82; font-size: .92rem;
    color: var(--text-color);
}

/* ---------- بطاقات المؤشرات (Glassmorphism) ---------- */
.stat-card {
    background: color-mix(in srgb, var(--secondary-background-color) 78%, transparent);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 20px;
    padding: 16px 14px;
    text-align: center;
    box-shadow: 0 8px 22px rgba(0,0,0,0.16), inset 0 1px 0 rgba(255,255,255,0.10);
    transition: transform .18s ease, box-shadow .18s ease;
    height: 100%;
}
.stat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 14px 30px rgba(0,0,0,0.24);
}
.stat-card .sc-icon { font-size: 1.6rem; line-height: 1; }
.stat-card .sc-value {
    font-size: 1.7rem; font-weight: 900; margin-top: 6px;
    color: var(--text-color);
}
.stat-card .sc-label {
    font-size: .82rem; opacity: .80; margin-top: 4px;
    color: var(--text-color);
}
.sc-danger  { border-color: rgba(239,68,68,.55); }
.sc-warning { border-color: rgba(245,158,11,.55); }
.sc-ok      { border-color: rgba(34,197,94,.45); }

/* ---------- لوحات زجاجية عامة ---------- */
.glass-panel {
    background: color-mix(in srgb, var(--secondary-background-color) 72%, transparent);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 18px;
    padding: 14px 16px;
    margin: 10px 0;
    box-shadow: 0 6px 18px rgba(0,0,0,0.14);
    color: var(--text-color);
}
.lock-screen {
    text-align: center; padding: 42px 20px; margin-top: 8vh;
}
.lock-screen .lock-icon { font-size: 3.4rem; }

/* ---------- الأزرار ---------- */
.stButton button, .stDownloadButton button {
    border-radius: 14px !important;
    font-weight: 700 !important;
    padding: .5rem 1rem !important;
    border: 1px solid rgba(128,128,128,.28) !important;
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 18px rgba(0,0,0,.20);
}

/* ---------- شارات الحالة ---------- */
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: .76rem; font-weight: 700; margin: 2px;
}
.badge-danger  { background: rgba(239,68,68,.20);  color: #ef4444; }
.badge-warning { background: rgba(245,158,11,.20); color: #f59e0b; }
.badge-ok      { background: rgba(34,197,94,.20);  color: #22c55e; }

/* ---------- عرض قابل للتمرير أفقياً للجداول العريضة على الجوال ---------- */
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }

/* ---------- تجاوب الجوال ---------- */
@media (max-width: 768px) {
    .block-container {
        padding: 0.8rem 0.6rem !important;
        padding-bottom: 104px !important;   /* مساحة للشريط السفلي العائم */
        max-width: 100vw !important;
        overflow-x: hidden;
    }
    .app-header { padding: 14px; border-radius: 16px; }
    .app-header h1 { font-size: 1.1rem; line-height: 1.4; }
    .app-header p { font-size: .82rem; }
    .stat-card { padding: 12px 8px; border-radius: 16px; }
    .stat-card .sc-value { font-size: 1.15rem; }
    .stat-card .sc-label { font-size: .68rem; }
    .stButton button, .stDownloadButton button { width: 100%; white-space: normal; }
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 8px !important;
    }
    [data-testid="column"] { min-width: 100% !important; }
    .glass-panel { padding: 12px 14px; font-size: .92rem; }
    h1 { font-size: 1.3rem !important; }
    h2, .stSubheader { font-size: 1.05rem !important; }
    h3 { font-size: .98rem !important; }
    [data-testid="stDataFrame"] { font-size: .82rem; }
}

/* عمود واحد لبطاقات المؤشرات على الشاشات الصغيرة جداً */
@media (max-width: 420px) {
    [data-testid="column"] { min-width: 48% !important; }
}

/* ---------- الشريط العائم الزجاجي الموحّد للتنقل ----------
   عمودي عائم على جانب الشاشة في اللابتوب، وأفقي عائم أسفل الشاشة في
   الجوال — بنفس المكوّن البرمجي، والفرق كله عبر media queries. تُضبط
   خصائص --active-index و --count من بايثون في كل تشغيل لتحريك المؤشر
   الدائري الشفاف بسلاسة (transition) بين الأقسام دون أي وميض أو تعليق،
   لأن حاوية الشريط تحافظ على هويتها البصرية بين مرات إعادة التشغيل. */
.st-key-floating_nav {
    position: fixed;
    z-index: 9999;
    background: color-mix(in srgb, var(--secondary-background-color) 66%, transparent);
    backdrop-filter: blur(22px);
    -webkit-backdrop-filter: blur(22px);
    border: 1px solid rgba(255,255,255,0.20);
    box-shadow: 0 14px 34px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.10);
}
.st-key-floating_nav .stButton button {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    color: var(--text-color) !important;
}
.st-key-floating_nav .stButton button span,
.st-key-floating_nav .stButton button p,
.st-key-floating_nav .stButton button div {
    color: var(--text-color) !important;
    opacity: .62;
    transition: opacity .25s ease, transform .25s ease;
}
.st-key-floating_nav .stButton button:hover span { opacity: 1; transform: scale(1.08); }
.st-key-floating_nav [data-testid="stCaptionContainer"] p {
    opacity: .68;
    transition: opacity .25s ease;
}

/* الجوال: كبسولة أفقية أسفل الشاشة */
@media (max-width: 768px) {
    .block-container { padding-bottom: 108px !important; }
    .st-key-floating_nav {
        display: block !important;
        right: 50%;
        transform: translateX(50%);
        bottom: 14px;
        width: min(97vw, 520px);
        border-radius: 999px;
        padding: 8px 6px 4px;
    }
    .st-key-floating_nav [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 0 !important;
        align-items: center;
        position: relative;
        z-index: 1;
    }
    .st-key-floating_nav [data-testid="column"] { min-width: 0 !important; flex: 1 1 0 !important; }
    .st-key-floating_nav .stButton { margin: 0; }
    .st-key-floating_nav .stButton button {
        border-radius: 999px !important;
        font-size: 1.2rem !important;
        line-height: 1;
        padding: 8px 2px 2px !important;
        width: 100% !important;
    }
    .st-key-floating_nav [data-testid="stCaptionContainer"] { text-align: center; margin-top: -8px; }
    .st-key-floating_nav [data-testid="stCaptionContainer"] p { font-size: .6rem !important; }
    /* المؤشر المتحرك: دائرة شفافة تنزلق أفقياً خلف الأيقونة النشطة.
       الحاوية RTL فتُبنى الأعمدة من اليمين، لذا التموضع من اليمين
       والانزلاق باتجاه سالب مع تزايد رقم القسم. */
    .st-key-floating_nav::before {
        content: "";
        position: absolute;
        top: 6px; bottom: 4px; right: 6px;
        width: calc((100% - 12px) / var(--nav-count, 6));
        background: color-mix(in srgb, var(--primary-color, #1f6feb) 30%, transparent);
        border: 1px solid color-mix(in srgb, var(--primary-color, #1f6feb) 45%, transparent);
        border-radius: 999px;
        transform: translateX(calc(var(--nav-index, 0) * -100%));
        transition: transform .35s cubic-bezier(.4,0,.2,1);
        z-index: 0;
    }
}

/* اللابتوب: عمود رأسي عائم على حافة الشاشة */
@media (min-width: 769px) {
    .block-container { padding-inline-end: 84px !important; }
    .st-key-floating_nav {
        display: block !important;
        top: 50%;
        right: 18px;
        transform: translateY(-50%);
        border-radius: 30px;
        padding: 14px 8px;
        width: 62px;
    }
    .st-key-floating_nav [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-floating_nav [data-testid="stVerticalBlock"] {
        gap: .35rem !important;
        position: relative;
        z-index: 1;
    }
    /* st.columns() ينتج دائماً صفاً أفقياً (stHorizontalBlock) بصرف النظر
       عن حجم الشاشة؛ على اللابتوب نجبره ليصطف عمودياً فوق بعضه لأن هذا
       المكوّن نفسه يُستخدم للشكلين (الأفقي في الجوال والعمودي هنا). بدون
       هذا التجاوز كانت الأيقونات الست ستنضغط أفقياً داخل عرض 62px فقط. */
    .st-key-floating_nav [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        flex-wrap: nowrap !important;
        gap: .35rem !important;
        align-items: center;
        position: relative;
        z-index: 1;
    }
    .st-key-floating_nav [data-testid="column"] {
        width: 100% !important;
        min-width: 0 !important;
        flex: 0 0 auto !important;
    }
    .st-key-floating_nav .stButton button {
        border-radius: 999px !important;
        font-size: 1.35rem !important;
        padding: 10px !important;
        width: 46px !important;
        height: 46px !important;
    }
    .st-key-floating_nav [data-testid="stCaptionContainer"] { display: none; }
    /* المؤشر المتحرك: دائرة شفافة تنزلق رأسياً خلف الأيقونة النشطة */
    .st-key-floating_nav::before {
        content: "";
        position: absolute;
        right: 8px; left: 8px;
        height: calc((100% - 16px) / var(--nav-count, 6));
        top: 14px;
        background: color-mix(in srgb, var(--primary-color, #1f6feb) 30%, transparent);
        border: 1px solid color-mix(in srgb, var(--primary-color, #1f6feb) 45%, transparent);
        border-radius: 999px;
        transform: translateY(calc(var(--nav-index, 0) * 100%));
        transition: transform .35s cubic-bezier(.4,0,.2,1);
        z-index: 0;
    }
}

footer {visibility: hidden;}
</style>
"""


# ---------------------------------------------------------------------------
# عرض آمن للجداول (يمنع ظهور نقاط/رموز بدل القيم الحقيقية بسبب اختلاط الأنواع)
# ---------------------------------------------------------------------------
TEXT_COLUMNS = {
    "التاريخ", "تفاصيل الزفات", "الوقت المستغرق", "الحالة",
    "بداية الدورة", "آخر تحديث", "ملاحظة", "الوقت", "تاريخ بداية الدورة",
    "معرف السجل", "رقم الدفعة",
}
INT_COLUMNS = {
    "عدد الزفات", "دورة الزيت", "الدورة المنتهية", "عدد أيام العمل",
    "إجمالي الزفات", "عدد العمليات",
}
FLOAT_COLUMNS = {
    "المسافة المقطوعة (كم)", "عداد الزيت الحالي", "حد تغيير الزيت",
    "المتبقي (كم)", "إجمالي المسافة (كم)", "متوسط المسافة اليومية (كم)",
    "آخر عداد زيت", "العداد عند الإغلاق", "الحد المعتمد",
}


def safe_table(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    يفرض أنواع بيانات ثابتة لكل عمود قبل العرض في st.dataframe.

    السبب: عمود من نوع object يحتوي أنواعاً مختلطة (نص/رقم/فارغ) قد لا يُحوَّل
    بنجاح إلى صيغة Arrow، فتظهر بعض الخلايا كنقطة "•" أو رمز غير مفهوم بدل
    القيمة الحقيقية (رقم السيارة أو عدد الزفات). هذه الدالة تضمن أن كل عمود
    نصي يبقى نصاً صريحاً، وكل عمود رقمي يتحول لرقم صريح، بلا أي تغيير للقيم.
    """
    if df is None or len(df) == 0:
        return df
    df = df.copy()
    if "رقم السيارة" in df.columns:
        # يحوَّل لعدد صحيح متى أمكن (الحالة الغالبة) ليُرتَّب عددياً
        # تصاعدياً (1، 2، 13، 14) بدل الترتيب الأبجدي (1، 13، 14، 2).
        df = util.numeric_plate_column(df, "رقم السيارة")
    for col in df.columns:
        if col == "رقم السيارة":
            continue
        if col in TEXT_COLUMNS:
            df[col] = df[col].astype(str).replace(
                {"nan": "", "None": "", "NaT": "", "<NA>": ""})
        elif col in INT_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
        elif col in FLOAT_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")
        elif df[col].dtype == object:
            # أي عمود آخر غير مصنّف: تثبيته كنص لتفادي فشل تحويل Arrow
            df[col] = df[col].astype(str).replace(
                {"nan": "", "None": "", "NaT": "", "<NA>": ""})
    return df


def nav_indicator_css(index: int, count: int) -> str:
    """تحديد موضع المؤشر الدائري المتحرك في الشريط العائم لهذا التشغيل —
    يُبنى كقاعدة CSS خارجية بدل style مضمّن لأن حاوية st.container(key=...)
    لا تقبل تمرير سمات style مباشرة من بايثون."""
    return (
        f'<style>.st-key-floating_nav {{ '
        f'--nav-index: {index}; --nav-count: {count}; }}</style>'
    )


def stat_card(icon: str, value, label: str, tone: str = "ok") -> str:
    """يُنتج بطاقة مؤشر زجاجية."""
    tone_class = {"danger": "sc-danger", "warning": "sc-warning"}.get(tone, "sc-ok")
    return (
        f'<div class="stat-card {tone_class}">'
        f'<div class="sc-icon">{icon}</div>'
        f'<div class="sc-value">{value}</div>'
        f'<div class="sc-label">{label}</div>'
        f'</div>'
    )


def header(title: str, subtitle: str = "") -> str:
    return (
        f'<div class="app-header"><h1>{title}</h1>'
        f'<p>{subtitle}</p></div>'
    )


def panel(html: str) -> str:
    return f'<div class="glass-panel">{html}</div>'
