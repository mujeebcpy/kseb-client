# KSEB Client

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-quality Python SDK for interacting with KSEB (Kerala State Electricity Board) web services. Designed to be reusable across ERPNext, FastAPI, Flask, Django, desktop apps, CLI tools, and other Python projects.

## Features

- 🔄 **Automatic Retries** with exponential backoff
- 📄 **PDF Parsing** without temporary files
- 🎯 **Type Hints** throughout the codebase
- 🚫 **No Print Statements** - uses Python logging
- 🔒 **Exception Handling** with meaningful custom exceptions
- 🧪 **Framework Agnostic** - works with FastAPI, Flask, Django, ERPNext, CLI, and more
- 🔌 **Single Session** for all HTTP communication
- ⚙️ **Fully Configurable** - timeout, retries, backoff

## Installation

### Using uv (Recommended)

```bash
uv add git+https://github.com/mujeebcpy/kseb-client.git
```

### From Source

```bash
git clone https://github.com/mujeebcpy/kseb-client.git
cd kseb-client
pip install -e .
```

### With Development Dependencies

```bash
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

KSEB protects the bill with an image CAPTCHA and the transformer lookup with Cloudflare
Turnstile, so a person has to complete both. Show the bill captcha image to the user and
pass the answer back with its session ID. For the transformer, pass the
`cf-turnstile-response` token the person got by completing the Turnstile check on the
[KSEB DTR Capacity page](https://wss.kseb.in/selfservices/reCap).

```python
from kseb_client import KSEBClient

# Initialize client
client = KSEBClient()

# Fetch the bill captcha and let the user solve it
bill_captcha = client.get_bill_captcha()
with open("bill_captcha.png", "wb") as f:
    f.write(bill_captcha.image)

# Get complete grid capacity information
result = client.get_grid_capacity(
    consumer_no="1145657015077",
    mobile="9895672251",
    bill_captcha_code=input("Bill captcha (bill_captcha.png): ").strip(),
    bill_session_id=bill_captcha.session_id,
    turnstile_token=input("Turnstile token (cf-turnstile-response): ").strip(),
)

# Access the results
print(f"Section: {result.section.section}")
print(f"Consumer: {result.bill.consumer_name}")
print(f"Transformer: {result.transformer.transformer_name}")
print(f"Available Balance: {result.transformer.balance_available}")
```

### Using Context Manager

```python
from kseb_client import KSEBClient

with KSEBClient() as client:
    section = client.get_section("1145657015077")
    print(section.section)
```

### CAPTCHA and Turnstile Lifecycle

- `BillCaptcha.session_id` is a plain string. Store it with the user's request (session,
  form field, cache) and send it back with the answer. It works from any `KSEBClient`
  instance, so a web app can show the captcha in one request and submit it in another.
- Each captcha can be submitted once. After a wrong answer (`KSEBCaptchaError`), fetch a new one.
- The bill `session_id` expires after about 2 hours.
- A Turnstile token works once and expires after a few minutes. When KSEB rejects it, the
  SDK raises `KSEBTurnstileError` (a subclass of `KSEBCaptchaError`) with KSEB's message,
  for example `Turnstile verification failed: Verification failed. Complete the Cloudflare
  check again.` Show that message and have the person complete the check again.

### Advanced Configuration

```python
from kseb_client import KSEBClient

# Configure with custom timeout, retries, and backoff
client = KSEBClient(
    timeout=20,              # HTTP timeout in seconds
    retries=5,               # Number of retries (GET requests only)
    backoff_factor=0.5,      # Exponential backoff multiplier
)

section = client.get_section("1145657015077")
client.close()
```

## API Reference

### KSEBClient

The main class for interacting with KSEB services.

#### Methods

##### `get_section(consumer_no: str) -> SectionInfo`

Get section details for a consumer.

```python
section = client.get_section("1145657015077")
print(section.section)        # Section name
print(section.division)       # Division name
print(section.phone)          # Phone number
print(section.email)          # Email address
```

**Raises:**
- `KSEBValidationError` - Invalid consumer number
- `KSEBAPIError` - API request failed
- `KSEBSectionNotFoundError` - Section not found

---

##### `get_bill_captcha() -> BillCaptcha`

Fetch the CAPTCHA required for bill download. `BillCaptcha.image` holds the PNG bytes, and
`BillCaptcha.session_id` is the KSEB session the answer is stored in. Keep `session_id`
with the user's request (for example in your own session) and pass it to `download_bill()`.
A captcha can be submitted only once. After a failed attempt, fetch a new one.

##### `download_bill(consumer_no: str, mobile: str, *, captcha_code: str, session_id: str) -> bytes`

Download bill PDF for a consumer.

```python
captcha = client.get_bill_captcha()
# Display captcha.image in your application and ask the user to solve it.
pdf_bytes = client.download_bill(
    "1145657015077",
    "9895672251",
    captcha_code=input("Captcha: ").strip(),
    session_id=captcha.session_id,
)
with open("bill.pdf", "wb") as f:
    f.write(pdf_bytes)
```

**Raises:**
- `KSEBValidationError` - Invalid inputs
- `KSEBCaptchaError` - Wrong or expired captcha answer
- `KSEBAuthenticationError` - Invalid consumer number or mobile
- `KSEBBillDownloadError` - Download failed

---

##### `parse_bill(pdf_bytes: bytes, consumer_no: str) -> BillInfo`

Extract information from a bill PDF.

```python
bill = client.parse_bill(pdf_bytes, "1145657015077")
print(bill.consumer_name)     # Name of consumer
print(bill.dtr)              # Distribution transformer
print(bill.connected_load)   # Connected load
print(bill.tariff)           # Tariff category
```

**Returns:**
- `BillInfo` with consumer name, section, DTR, connected load, and tariff

---

##### `get_transformer(consumer_no: str, *, turnstile_token: str, section_info: SectionInfo | None = None) -> Transformer`

Get the transformer serving a consumer, with its solar capacity. KSEB looks the
transformer up from the consumer number, so no transformer name matching is needed.

```python
dtr = client.get_transformer(
    "1145657015077",
    turnstile_token=input("Turnstile token (cf-turnstile-response): ").strip(),
)
print(f"Transformer: {dtr.transformer_name} ({dtr.capacity_kva} kVA)")
print(f"Allowed solar: {dtr.allowed_cap} kW")
print(f"Grid connected: {dtr.comp_cap} kW")
print(f"Balance: {dtr.balance_available} kW (as on {dtr.as_on})")
```

**Parameters:**
- `consumer_no` - 13-digit consumer number
- `turnstile_token` - `cf-turnstile-response` from the Turnstile check on the KSEB website (single use)
- `section_info` - Optional `SectionInfo` used to fill in division and subdivision

**Raises:**
- `KSEBValidationError` - Invalid consumer number or empty token
- `KSEBTurnstileError` - KSEB rejected the Turnstile token
- `KSEBAPIError` - KSEB returned another error (for example an unknown consumer)

---

##### `get_grid_capacity(consumer_no: str, mobile: str, *, bill_captcha_code: str, bill_session_id: str, turnstile_token: str) -> GridCapacityResult`

Complete high-level helper that combines all operations.

Steps:
1. Fetches section details
2. Downloads and parses bill
3. Fetches the consumer's transformer

```python
bill_captcha = client.get_bill_captcha()
# Show the captcha image to the user and collect the answer and the Turnstile token.
result = client.get_grid_capacity(
    "1145657015077",
    "9895672251",
    bill_captcha_code=input("Bill captcha: ").strip(),
    bill_session_id=bill_captcha.session_id,
    turnstile_token=input("Turnstile token: ").strip(),
)

print(f"Section: {result.section.section}")
print(f"Consumer: {result.bill.consumer_name}")
print(f"DTR: {result.transformer.transformer_name}")
print(f"Available: {result.transformer.balance_available} kW")
```

**Returns:**
- `GridCapacityResult` with section, bill, and transformer info

**Raises:**
- Any exception from underlying operations

##### `get_grid_capacity_options(consumer_no: str, *, turnstile_token: str) -> GridCapacityOptionsResult`

Bill-free lookup for when bill download is unavailable. It fetches section details and
the consumer's transformer. It returns no bill-derived address or consumer details.

```python
result = client.get_grid_capacity_options(
    "1145657015077",
    turnstile_token=input("Turnstile token: ").strip(),
)
print(result.section.section)
for transformer in result.transformers:
    print(transformer.transformer_name, transformer.balance_available)
```

The result contains `section` and `transformers` fields. KSEB now returns only the
consumer's own transformer, so `transformers` holds one item.

---

##### `close() -> None`

Close the client and release resources.

```python
client.close()
```

---

### Models

All models are dataclasses providing type-safe access to data.

#### `SectionInfo`

```python
@dataclass
class SectionInfo:
    office_code: str
    section: str
    subdivision: str
    subdivision_email: str
    division: str
    division_phone: str
    division_email: str
    phone: str
    email: str
```

#### `BillInfo`

```python
@dataclass
class BillInfo:
    consumer_no: str
    consumer_name: str
    section: str
    dtr: str
    connected_load: str | None = None
    tariff: str | None = None
```

#### `Transformer`

```python
@dataclass
class Transformer:
    transformer_name: str
    division: str
    sub_division: str
    allowed_cap: float                # Solar capacity KSEB allows on the transformer (kW)
    comp_cap: float                   # Capacity already grid connected (kW)
    regi: float                       # Always 0: KSEB no longer reports it separately
    balance_available: float          # Remaining capacity reported by KSEB (kW)
    capacity_kva: float | None = None # Transformer rating (kVA)
    as_on: str | None = None          # Date the figures are valid for
```

#### `GridCapacityResult`

```python
@dataclass
class GridCapacityResult:
    section: SectionInfo
    bill: BillInfo
    transformer: Transformer
```

### Exceptions

All exceptions inherit from `KSEBClientError`.

| Exception | Usage |
|-----------|-------|
| `KSEBClientError` | Base exception for all SDK errors |
| `KSEBAPIError` | API returns error or unexpected response |
| `KSEBNetworkError` | Network issues (timeout, connection error) |
| `KSEBAuthenticationError` | Authentication fails (invalid credentials) |
| `KSEBValidationError` | Input validation fails |
| `KSEBParsingError` | Data parsing fails (PDF, HTML, JSON) |
| `KSEBBillDownloadError` | Bill download fails |
| `KSEBCaptchaError` | Captcha answer is wrong or expired |
| `KSEBTurnstileError` | Turnstile token is missing, used or expired (subclass of `KSEBCaptchaError`) |
| `KSEBSectionNotFoundError` | Section not found |

```python
from kseb_client import KSEBClient, KSEBValidationError, KSEBSectionNotFoundError

client = KSEBClient()

try:
    section = client.get_section("invalid")
except KSEBValidationError as e:
    print(f"Invalid input: {e}")
except KSEBSectionNotFoundError as e:
    print(f"Section not found: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Logging

The SDK uses Python's standard `logging` module. Enable logging to see debug information:

```python
import logging
from kseb_client import KSEBClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

client = KSEBClient()
captcha = client.get_bill_captcha()
pdf_bytes = client.download_bill(
    "1145657015077",
    "9895672251",
    captcha_code=input("Captcha: ").strip(),
    session_id=captcha.session_id,
)
```

Output:
```
DEBUG:kseb_client.client:KSEBClient initialized: timeout=15s, retries=3, backoff=0.3
DEBUG:kseb_client.session:GET https://kseb.in/captcha/default
Captcha: 7pnd
DEBUG:kseb_client.bill:Downloading bill for consumer: 1145657015077
DEBUG:kseb_client.session:GET https://kseb.in/knowyourbilldetail
INFO:kseb_client.bill:Bill downloaded successfully (8899 bytes)
```

## Integration Examples

Web apps need two steps because a person has to solve the captcha and the Turnstile check:

1. **Get captcha.** The server returns the bill captcha image and its session ID. The frontend shows the image.
2. **Submit.** The frontend sends the consumer details, the captcha answer, the session ID and the
   Turnstile token back.

One `KSEBClient` can be shared by all requests, because the captcha session ID and Turnstile
token travel with the request and no per-user state is kept in the client. If the captcha or
token is rejected, both are used up, so the frontend should fetch a new captcha and have the
person complete the Turnstile check again (`KSEBCaptchaError` / `KSEBTurnstileError`, HTTP 422 below).

### FastAPI

```python
import base64

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kseb_client import KSEBCaptchaError, KSEBClient, KSEBClientError

app = FastAPI()
client = KSEBClient()


def data_uri(image: bytes, content_type: str | None) -> str:
    return f"data:{content_type or 'image/png'};base64,{base64.b64encode(image).decode()}"


class GridCapacityRequest(BaseModel):
    consumer_no: str
    mobile: str
    bill_captcha_code: str
    bill_session_id: str
    turnstile_token: str


# Plain `def` endpoints: the SDK is blocking, so FastAPI runs them in a thread pool.
@app.get("/captchas")
def get_captchas():
    bill = client.get_bill_captcha()
    return {
        "bill_session_id": bill.session_id,
        "bill_captcha": data_uri(bill.image, bill.content_type),
    }


@app.post("/grid-capacity")
def get_grid_capacity(body: GridCapacityRequest):
    try:
        result = client.get_grid_capacity(
            body.consumer_no,
            body.mobile,
            bill_captcha_code=body.bill_captcha_code,
            bill_session_id=body.bill_session_id,
            turnstile_token=body.turnstile_token,
        )
    except KSEBCaptchaError as e:
        raise HTTPException(status_code=422, detail=f"{e} Fetch a new captcha, complete the Turnstile check again and retry.")
    except KSEBClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "section": result.section.section,
        "consumer": result.bill.consumer_name,
        "transformer": result.transformer.transformer_name,
        "balance": result.transformer.balance_available,
    }
```

### Flask

```python
import base64

from flask import Flask, jsonify, request
from kseb_client import KSEBCaptchaError, KSEBClient, KSEBClientError

app = Flask(__name__)
client = KSEBClient()

FIELDS = ("consumer_no", "mobile", "bill_captcha_code", "bill_session_id", "turnstile_token")


def data_uri(image, content_type):
    return f"data:{content_type or 'image/png'};base64,{base64.b64encode(image).decode()}"


@app.get("/api/captchas")
def get_captchas():
    bill = client.get_bill_captcha()
    return jsonify({
        "bill_session_id": bill.session_id,
        "bill_captcha": data_uri(bill.image, bill.content_type),
    })


@app.post("/api/grid-capacity")
def get_grid_capacity():
    data = request.get_json(silent=True) or {}
    missing = [field for field in FIELDS if not data.get(field)]
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    try:
        result = client.get_grid_capacity(
            data["consumer_no"],
            data["mobile"],
            bill_captcha_code=data["bill_captcha_code"],
            bill_session_id=data["bill_session_id"],
            turnstile_token=data["turnstile_token"],
        )
    except KSEBCaptchaError as e:
        return {"error": f"{e} Fetch a new captcha, complete the Turnstile check again and retry."}, 422
    except KSEBClientError as e:
        return {"error": str(e)}, 400
    return jsonify({
        "section": result.section.section,
        "consumer": result.bill.consumer_name,
        "transformer": result.transformer.transformer_name,
        "balance": result.transformer.balance_available,
    })
```

### CLI Tool

```python
import sys

from kseb_client import KSEBCaptchaError, KSEBClient


def ask_captcha(image: bytes, path: str, label: str) -> str:
    with open(path, "wb") as f:
        f.write(image)
    return input(f"{label} captcha (open {path}): ").strip()


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <consumer_no> <mobile>")
        sys.exit(1)

    consumer_no, mobile = sys.argv[1], sys.argv[2]

    with KSEBClient() as client:
        while True:
            bill = client.get_bill_captcha()
            try:
                result = client.get_grid_capacity(
                    consumer_no,
                    mobile,
                    bill_captcha_code=ask_captcha(bill.image, "bill_captcha.png", "Bill"),
                    bill_session_id=bill.session_id,
                    turnstile_token=input(
                        "Turnstile token from https://wss.kseb.in/selfservices/reCap: "
                    ).strip(),
                )
                break
            except KSEBCaptchaError as e:
                print(f"{e} Trying again.")

        print(f"Section: {result.section.section}")
        print(f"Consumer: {result.bill.consumer_name}")
        print(f"Available Balance: {result.transformer.balance_available} kVA")


if __name__ == "__main__":
    main()
```

### Django

```python
import base64
import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from kseb_client import KSEBCaptchaError, KSEBClient, KSEBClientError

client = KSEBClient()

FIELDS = ("consumer_no", "mobile", "bill_captcha_code", "bill_session_id", "turnstile_token")


def data_uri(image, content_type):
    return f"data:{content_type or 'image/png'};base64,{base64.b64encode(image).decode()}"


@require_GET
def get_captchas(request):
    bill = client.get_bill_captcha()
    return JsonResponse({
        "bill_session_id": bill.session_id,
        "bill_captcha": data_uri(bill.image, bill.content_type),
    })


@require_POST
def get_grid_capacity(request):
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    missing = [field for field in FIELDS if not data.get(field)]
    if missing:
        return JsonResponse({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

    try:
        result = client.get_grid_capacity(
            data["consumer_no"],
            data["mobile"],
            bill_captcha_code=data["bill_captcha_code"],
            bill_session_id=data["bill_session_id"],
            turnstile_token=data["turnstile_token"],
        )
    except KSEBCaptchaError as e:
        return JsonResponse({"error": f"{e} Fetch a new captcha, complete the Turnstile check again and retry."}, status=422)
    except KSEBClientError as e:
        return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({
        "section": result.section.section,
        "consumer": result.bill.consumer_name,
        "transformer": result.transformer.transformer_name,
        "balance": result.transformer.balance_available,
    })
```

With Django's CSRF protection on, the POST view needs a CSRF token from the frontend, or
`@csrf_exempt` if the endpoint is called by another service.

## Known Limitations

1. **API Dependency**: The SDK relies on KSEB's unofficial web endpoints. Changes to their website structure may break functionality.

2. **PDF Parsing**: Bill parsing works for the current KSEB PDF format. Format changes will require updates to the parser.

3. **Turnstile**: The transformer lookup needs a Cloudflare Turnstile token, which a person gets
   by completing the check on the KSEB website. The SDK cannot obtain one by itself.

4. **Rate Limiting**: No built-in rate limiting. KSEB may have undocumented rate limits.

5. **Mobile Number Association**: The API requires a mobile number associated with the consumer account.

## Error Handling Best Practices

```python
from kseb_client import (
    KSEBClient,
    KSEBValidationError,
    KSEBCaptchaError,
    KSEBTurnstileError,
    KSEBAuthenticationError,
    KSEBNetworkError,
    KSEBClientError
)

client = KSEBClient()
bill_captcha = client.get_bill_captcha()
# ... show the image to the user and collect bill_answer and turnstile_token ...

try:
    result = client.get_grid_capacity(
        "1145657015077",
        "9895672251",
        bill_captcha_code=bill_answer,
        bill_session_id=bill_captcha.session_id,
        turnstile_token=turnstile_token,
    )
except KSEBValidationError as e:
    # Handle invalid input
    print(f"Invalid input: {e.message} (field: {e.field})")
except KSEBTurnstileError as e:
    # Turnstile token rejected - have the person complete the Cloudflare check again
    print(e)
except KSEBCaptchaError as e:
    # Wrong or expired captcha answer - fetch a new captcha and ask again
    print(f"Captcha rejected: {e}")
except KSEBAuthenticationError as e:
    # Handle authentication failure
    print("Invalid consumer number or mobile number")
except KSEBNetworkError as e:
    # Handle network issues (retries already attempted)
    print("Network error - please try again later")
except KSEBClientError as e:
    # Handle other SDK errors
    print(f"SDK error: {e}")
except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")
```

## Performance Tips

1. **Reuse Client**: Create one client instance and reuse it across your application to keep
   connection pooling. Captcha IDs and Turnstile tokens are passed explicitly, so a shared
   client is safe for concurrent users.

```python
# Good - reuse client
client = KSEBClient()
for consumer_no in consumer_list:
    section = client.get_section(consumer_no)

# Avoid - creating new clients
for consumer_no in consumer_list:
    client = KSEBClient()
    section = client.get_section(consumer_no)
```

2. **Adjust Timeout**: Increase timeout for slower networks or during peak hours.

```python
client = KSEBClient(timeout=30)  # 30 seconds instead of default 15
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial SDK. It is not affiliated with or endorsed by KSEB. Use at your own risk.

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review example code in `examples/` directory

---

**Made with ❤️ for the Kerala developer community**
