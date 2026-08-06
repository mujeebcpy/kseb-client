"""
Constants and configuration for KSEB Client SDK.

This module contains all endpoint URLs, configuration defaults, and other constants
used throughout the SDK.
"""

# API Endpoints
BASE_URL = "https://old.kseb.in/billview/"
BILL_VIEW_URL = f"{BASE_URL}index.php"
SECTION_URL = "https://kseb.in/knowursectiondetail"
DTR_AVAILABLE_URL = "https://wss.kseb.in/selfservices/getDTRAvailable"

# HTTP Configuration
DEFAULT_TIMEOUT = 15  # seconds
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.3  # exponential backoff multiplier

# Caching Configuration
DEFAULT_CACHE_TTL = 15 * 60  # 15 minutes in seconds
CACHE_KEY_TRANSFORMERS = "transformers:{section_code}"

# Form Field Names
FORM_FIELD_CONSUMER_NO = "consumerno"
FORM_FIELD_MOBILE = "regmobno"
FORM_FIELD_OKE_KEY = "okey"
FORM_FIELD_SUBMIT = "b_submit_0"
FORM_SUBMIT_VALUE = "View Bill"

# Response Content Types
CONTENT_TYPE_PDF = "application/pdf"
CONTENT_TYPE_JSON = "application/json"

# HTTP Headers
USER_AGENT = "KSEB-Client/1.0 (+https://github.com/your-username/kseb-client)"
