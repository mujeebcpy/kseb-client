# KSEB Client

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-quality Python SDK for interacting with KSEB (Kerala State Electricity Board) web services. Designed to be reusable across ERPNext, FastAPI, Flask, Django, desktop apps, CLI tools, and other Python projects.

## Features

- 🔄 **Automatic Retries** with exponential backoff
- ⚡ **In-Memory Caching** for transformer data (configurable TTL)
- 📄 **PDF Parsing** without temporary files
- 🎯 **Type Hints** throughout the codebase
- 🚫 **No Print Statements** - uses Python logging
- 🔒 **Exception Handling** with meaningful custom exceptions
- 🧪 **Framework Agnostic** - works with FastAPI, Flask, Django, ERPNext, CLI, and more
- 🔌 **Single Session** for all HTTP communication
- ⚙️ **Fully Configurable** - timeout, retries, cache TTL

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

KSEB protects both the bill and the transformer lookup with a CAPTCHA, so a person has
to solve two images. Fetch them, show them to the user, and pass the answers back
together with the IDs that came with each image.

```python
from kseb_client import KSEBClient

# Initialize client
client = KSEBClient()

# Fetch both captchas and let the user solve them
bill_captcha = client.get_bill_captcha()
transformer_captcha = client.get_transformer_captcha()
with open("bill_captcha.png", "wb") as f:
    f.write(bill_captcha.image)
with open("transformer_captcha.png", "wb") as f:
    f.write(transformer_captcha.image)

# Get complete grid capacity information
result = client.get_grid_capacity(
    consumer_no="1145657015077",
    mobile="9895672251",
    bill_captcha_code=input("Bill captcha (bill_captcha.png): ").strip(),
    bill_session_id=bill_captcha.session_id,
    captcha_code=input("Transformer captcha (transformer_captcha.png): ").strip(),
    unique_id=transformer_captcha.unique_id,
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

### CAPTCHA Lifecycle

- `BillCaptcha.session_id` and `TransformerCaptcha.unique_id` are plain strings. Store them
  with the user's request (session, form field, cache) and send them back with the answers.
  They work from any `KSEBClient` instance, so a web app can show the captchas in one request
  and submit them in another.
- Each captcha can be submitted once. After a wrong answer (`KSEBCaptchaError`), fetch a new one.
- The bill `session_id` expires after about 2 hours.

### Advanced Configuration

```python
from kseb_client import KSEBClient

# Configure with custom timeout, retries, and cache TTL
client = KSEBClient(
    timeout=20,              # HTTP timeout in seconds
    retries=5,               # Number of retries
    backoff_factor=0.5,      # Exponential backoff multiplier
    cache_ttl=1800           # Cache TTL in seconds (30 minutes)
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

##### `get_transformers(section_code: str, use_cache: bool = True, *, captcha_code: str, unique_id: str) -> list[Transformer]`

Get available transformers for a section.

```python
# Results are cached by default (15 minutes)
captcha = client.get_transformer_captcha()
captcha_code = input("Captcha: ").strip()
transformers = client.get_transformers(
    "1234", captcha_code=captcha_code, unique_id=captcha.unique_id
)

for dtr in transformers:
    print(f"{dtr.transformer_name}: {dtr.balance_available} kW available")
```

**Parameters:**
- `section_code` - 4-digit section code (extracted from consumer number)
- `use_cache` - Use cached results (default True)

**Returns:**
- List of `Transformer` objects

---

##### `find_transformer(section_code: str, transformer_name: str, *, captcha_code: str, unique_id: str) -> Transformer`

Find a specific transformer by name.

```python
captcha = client.get_transformer_captcha()
captcha_code = input("Captcha: ").strip()
dtr = client.find_transformer(
    "1234", "DTR-001", captcha_code=captcha_code, unique_id=captcha.unique_id
)
print(f"Balance: {dtr.balance_available} kW")
print(f"Allowed Capacity: {dtr.allowed_cap} kW")
```

**Returns:**
- `Transformer` object if found

**Raises:**
- `KSEBTransformerNotFoundError` - Transformer not found

---

##### `get_grid_capacity(consumer_no: str, mobile: str, *, bill_captcha_code: str, bill_session_id: str, captcha_code: str, unique_id: str) -> GridCapacityResult`

Complete high-level helper that combines all operations.

Steps:
1. Extracts section code from consumer number
2. Fetches section details
3. Downloads and parses bill
4. Fetches available transformers
5. Matches the consumer's transformer

```python
bill_captcha = client.get_bill_captcha()
transformer_captcha = client.get_transformer_captcha()
# Show both captcha images to the user and collect the answers.
result = client.get_grid_capacity(
    "1145657015077",
    "9895672251",
    bill_captcha_code=input("Bill captcha: ").strip(),
    bill_session_id=bill_captcha.session_id,
    captcha_code=input("Transformer captcha: ").strip(),
    unique_id=transformer_captcha.unique_id,
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

##### `get_grid_capacity_options(consumer_no: str, *, captcha_code: str, unique_id: str) -> GridCapacityOptionsResult`

Bill-free fallback for when bill download is unavailable. It fetches section details
and every transformer available in that section, so an application can let the user
search and choose one. It returns no bill-derived address or consumer details.

```python
captcha = client.get_transformer_captcha()
# Display captcha.image (PNG/JPEG bytes) in your application and ask the user to solve it.
captcha_code = input("Captcha: ").strip()
result = client.get_grid_capacity_options(
    "1145657015077",
    captcha_code=captcha_code,
    unique_id=captcha.unique_id,
)
print(result.section.section)
for transformer in result.transformers:
    print(transformer.transformer_name, transformer.balance_available)
```

The result contains `section` and `transformers` fields. Use the selected transformer's
capacity values from this list in your application. Fetch and submit the CAPTCHA using
the same `KSEBClient` instance so its session cookies are retained.

---

##### `clear_cache() -> None`

Clear the transformer cache manually.

```python
client.clear_cache()
```

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
    allowed_cap: float
    comp_cap: float
    regi: float
    balance_available: float
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
| `KSEBTransformerNotFoundError` | Transformer not found |
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
DEBUG:kseb_client.client:KSEBClient initialized: timeout=15s, retries=3, backoff=0.3, cache_ttl=900s
DEBUG:kseb_client.session:GET https://kseb.in/captcha/default
Captcha: 7pnd
DEBUG:kseb_client.bill:Downloading bill for consumer: 1145657015077
DEBUG:kseb_client.session:GET https://kseb.in/knowyourbilldetail
INFO:kseb_client.bill:Bill downloaded successfully (8899 bytes)
```

## Integration Examples

Web apps need two steps because a person has to solve the captchas:

1. **Get captchas.** The server returns both images and their IDs. The frontend shows the images.
2. **Submit.** The frontend sends the consumer details, both answers and both IDs back.

One `KSEBClient` can be shared by all requests, because the captcha IDs travel with the request
and no per-user state is kept in the client. If either answer is wrong, both captchas are used
up, so the frontend should fetch a new pair (`KSEBCaptchaError`, HTTP 422 below).

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
    captcha_code: str
    unique_id: str


# Plain `def` endpoints: the SDK is blocking, so FastAPI runs them in a thread pool.
@app.get("/captchas")
def get_captchas():
    bill = client.get_bill_captcha()
    transformer = client.get_transformer_captcha()
    return {
        "bill_session_id": bill.session_id,
        "bill_captcha": data_uri(bill.image, bill.content_type),
        "unique_id": transformer.unique_id,
        "transformer_captcha": data_uri(transformer.image, transformer.content_type),
    }


@app.post("/grid-capacity")
def get_grid_capacity(body: GridCapacityRequest):
    try:
        result = client.get_grid_capacity(
            body.consumer_no,
            body.mobile,
            bill_captcha_code=body.bill_captcha_code,
            bill_session_id=body.bill_session_id,
            captcha_code=body.captcha_code,
            unique_id=body.unique_id,
        )
    except KSEBCaptchaError as e:
        raise HTTPException(status_code=422, detail=f"{e} Fetch new captchas and try again.")
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

FIELDS = ("consumer_no", "mobile", "bill_captcha_code", "bill_session_id", "captcha_code", "unique_id")


def data_uri(image, content_type):
    return f"data:{content_type or 'image/png'};base64,{base64.b64encode(image).decode()}"


@app.get("/api/captchas")
def get_captchas():
    bill = client.get_bill_captcha()
    transformer = client.get_transformer_captcha()
    return jsonify({
        "bill_session_id": bill.session_id,
        "bill_captcha": data_uri(bill.image, bill.content_type),
        "unique_id": transformer.unique_id,
        "transformer_captcha": data_uri(transformer.image, transformer.content_type),
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
            captcha_code=data["captcha_code"],
            unique_id=data["unique_id"],
        )
    except KSEBCaptchaError as e:
        return {"error": f"{e} Fetch new captchas and try again."}, 422
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
            transformer = client.get_transformer_captcha()
            try:
                result = client.get_grid_capacity(
                    consumer_no,
                    mobile,
                    bill_captcha_code=ask_captcha(bill.image, "bill_captcha.png", "Bill"),
                    bill_session_id=bill.session_id,
                    captcha_code=ask_captcha(transformer.image, "transformer_captcha.png", "Transformer"),
                    unique_id=transformer.unique_id,
                )
                break
            except KSEBCaptchaError as e:
                print(f"{e} Trying again with new captchas.")

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

FIELDS = ("consumer_no", "mobile", "bill_captcha_code", "bill_session_id", "captcha_code", "unique_id")


def data_uri(image, content_type):
    return f"data:{content_type or 'image/png'};base64,{base64.b64encode(image).decode()}"


@require_GET
def get_captchas(request):
    bill = client.get_bill_captcha()
    transformer = client.get_transformer_captcha()
    return JsonResponse({
        "bill_session_id": bill.session_id,
        "bill_captcha": data_uri(bill.image, bill.content_type),
        "unique_id": transformer.unique_id,
        "transformer_captcha": data_uri(transformer.image, transformer.content_type),
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
            captcha_code=data["captcha_code"],
            unique_id=data["unique_id"],
        )
    except KSEBCaptchaError as e:
        return JsonResponse({"error": f"{e} Fetch new captchas and try again."}, status=422)
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

3. **Transformer Name Matching**: Matching is case-insensitive but exact - partial matches are not supported.

4. **Rate Limiting**: No built-in rate limiting. KSEB may have undocumented rate limits.

5. **Mobile Number Association**: The API requires a mobile number associated with the consumer account.

## Error Handling Best Practices

```python
from kseb_client import (
    KSEBClient,
    KSEBValidationError,
    KSEBCaptchaError,
    KSEBAuthenticationError,
    KSEBTransformerNotFoundError,
    KSEBNetworkError,
    KSEBClientError
)

client = KSEBClient()
bill_captcha = client.get_bill_captcha()
transformer_captcha = client.get_transformer_captcha()
# ... show both images to the user and collect bill_answer / transformer_answer ...

try:
    result = client.get_grid_capacity(
        "1145657015077",
        "9895672251",
        bill_captcha_code=bill_answer,
        bill_session_id=bill_captcha.session_id,
        captcha_code=transformer_answer,
        unique_id=transformer_captcha.unique_id,
    )
except KSEBValidationError as e:
    # Handle invalid input
    print(f"Invalid input: {e.message} (field: {e.field})")
except KSEBCaptchaError as e:
    # Wrong or expired captcha answer - fetch new captchas and ask again
    print(f"Captcha rejected: {e}")
except KSEBAuthenticationError as e:
    # Handle authentication failure
    print("Invalid consumer number or mobile number")
except KSEBTransformerNotFoundError as e:
    # Handle transformer not found
    print(f"Transformer not available: {e.transformer_name}")
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

1. **Use Caching**: Transformer lists are cached for 15 minutes by default. Disable caching only if you need fresh data.

```python
# Use cache (default)
captcha = client.get_transformer_captcha()
transformers = client.get_transformers(
    "1234", captcha_code=input("Captcha: ").strip(), unique_id=captcha.unique_id
)

# Bypass cache
captcha = client.get_transformer_captcha()
transformers = client.get_transformers(
    "1234", use_cache=False, captcha_code=input("Captcha: ").strip(), unique_id=captcha.unique_id
)

# Clear cache manually
client.clear_cache()
```

2. **Reuse Client**: Create one client instance and reuse it across your application to keep
   connection pooling and the transformer cache. Captcha IDs are passed explicitly, so a shared
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

3. **Adjust Timeout**: Increase timeout for slower networks or during peak hours.

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
