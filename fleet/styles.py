# -*- coding: utf-8 -*-
"""
التصميم البصري للتطبيق:
  * خط Cairo من Google Fonts على كل عناصر الواجهة.
  * أسلوب Glassmorphism (زجاج ضبابي + حدود شفافة + ظلال ثلاثية الأبعاد).
  * اعتماد حصري على متغيرات ثيم ستريملت الأصلية ليتبدّل الوضع
    النهاري/الداكن فوراً من قائمة الإعدادات (الثلاث نقاط ← Settings).
  * تجاوب كامل مع شاشات الجوال.
"""

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

/* ---------- تجاوب الجوال ---------- */
@media (max-width: 768px) {
    .block-container { padding: 0.8rem 0.6rem !important; }
    .app-header { padding: 14px; border-radius: 16px; }
    .app-header h1 { font-size: 1.15rem; }
    .stat-card { padding: 12px 8px; border-radius: 16px; }
    .stat-card .sc-value { font-size: 1.25rem; }
    .stat-card .sc-label { font-size: .72rem; }
    .stButton button, .stDownloadButton button { width: 100%; }
}
#MainMenu {visibility: visible;}
footer {visibility: hidden;}
</style>
"""


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
