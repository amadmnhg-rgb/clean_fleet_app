# -*- coding: utf-8 -*-
"""
نظام تسجيل الأحداث (Logging) للمشروع.

يوفر طريقة موحدة لتسجيل الأخطاء والتحذيرات والمعلومات
بدلاً من استخدام print() الذي لا يُستخدم في الإنتاج.
"""

import logging
import sys
from datetime import datetime

# إعداد اللوغر الرئيسي
logger = logging.getLogger("clean_fleet")
logger.setLevel(logging.INFO)

# منع التكرار إذا تم الاستيراد من عدة أماكن
if not logger.handlers:
    # تنسيق الرسائل بالعربية والإنجليزية
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # إخراج للوحدة الطرفية
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def log_error(message: str, exc_info=False):
    """تسجيل خطأ."""
    logger.error(message, exc_info=exc_info)


def log_warning(message: str):
    """تسجيل تحذير."""
    logger.warning(message)


def log_info(message: str):
    """تسجيل معلومة."""
    logger.info(message)


def log_debug(message: str):
    """تسجيل معلومة تفصيلية (للتطوير فقط)."""
    logger.debug(message)


def log_success(message: str):
    """تسجيل نجاح عملية."""
    logger.info(f"✅ {message}")


def log_operation(operation: str, details: str = ""):
    """تسجيل عملية مهمة."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{operation}] {details}" if details else f"[{operation}]"
    logger.info(msg)
