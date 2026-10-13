"""
Constants and configuration for KSEB Client SDK.

This module contains all endpoint URLs, configuration defaults, and other constants
used throughout the SDK.
"""

# API Endpoints
BILL_CAPTCHA_URL = "https://kseb.in/captcha/default"
BILL_DETAIL_URL = "https://kseb.in/knowyourbilldetail"
BILL_SESSION_COOKIE = "kseb_session"
SECTION_URL = "https://kseb.in/knowursectiondetail"
DTR_AVAILABLE_URL = "https://wss.kseb.in/selfservices/getDTRAvailable"
TRANSFORMER_CAPTCHA_URL = "https://wss.kseb.in/selfservices/captchaImg.image"

# HTTP Configuration
DEFAULT_TIMEOUT = 15  # seconds
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.3  # exponential backoff multiplier

# Caching Configuration
DEFAULT_CACHE_TTL = 15 * 60  # 15 minutes in seconds
CACHE_KEY_TRANSFORMERS = "transformers:{section_code}"

# Form Field Names
FORM_FIELD_CONSUMER_NO = "consumerno"
FORM_FIELD_MOBILE = "mobileno"
FORM_FIELD_CAPTCHA = "captcha"

# Response Content Types
CONTENT_TYPE_PDF = "application/pdf"
CONTENT_TYPE_JSON = "application/json"

# HTTP Headers
USER_AGENT = "KSEB-Client/1.0 (+https://github.com/mujeebcpy/kseb-client)"
