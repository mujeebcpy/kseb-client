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

```python
from kseb_client import KSEBClient

# Initialize client
client = KSEBClient()

# Get complete grid capacity information
result = client.get_grid_capacity(
    consumer_no="1145657015077",
    mobile="9895672251"
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
    result = client.get_grid_capacity("1145657015077", "9895672251")
    print(result.transformer.balance_available)
```

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

result = client.get_grid_capacity("1145657015077", "9895672251")
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

##### `download_bill(consumer_no: str, mobile: str) -> bytes`

Download bill PDF for a consumer.

```python
pdf_bytes = client.download_bill("1145657015077", "9895672251")
with open("bill.pdf", "wb") as f:
    f.write(pdf_bytes)
```

**Raises:**
- `KSEBValidationError` - Invalid inputs
- `KSEBAuthenticationError` - Invalid credentials
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

##### `get_transformers(section_code: str, use_cache: bool = True) -> list[Transformer]`

Get available transformers for a section.

```python
# Results are cached by default (15 minutes)
transformers = client.get_transformers("1234")

for dtr in transformers:
    print(f"{dtr.transformer_name}: {dtr.balance_available} kW available")
```

**Parameters:**
- `section_code` - 4-digit section code (extracted from consumer number)
- `use_cache` - Use cached results (default True)

**Returns:**
- List of `Transformer` objects

---

##### `find_transformer(section_code: str, transformer_name: str) -> Transformer`

Find a specific transformer by name.

```python
dtr = client.find_transformer("1234", "DTR-001")
print(f"Balance: {dtr.balance_available} kW")
print(f"Allowed Capacity: {dtr.allowed_cap} kW")
```

**Returns:**
- `Transformer` object if found

**Raises:**
- `KSEBTransformerNotFoundError` - Transformer not found

---

##### `get_grid_capacity(consumer_no: str, mobile: str) -> GridCapacityResult`

Complete high-level helper that combines all operations.

Steps:
1. Extracts section code from consumer number
2. Fetches section details
3. Downloads and parses bill
4. Fetches available transformers
5. Matches the consumer's transformer

```python
result = client.get_grid_capacity("1145657015077", "9895672251")

print(f"Section: {result.section.section}")
print(f"Consumer: {result.bill.consumer_name}")
print(f"DTR: {result.transformer.transformer_name}")
print(f"Available: {result.transformer.balance_available} kW")
```

**Returns:**
- `GridCapacityResult` with section, bill, and transformer info

**Raises:**
- Any exception from underlying operations

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
| `KSEBTransformerNotFoundError` | Transformer not found |
| `KSEBSectionNotFoundError` | Section not found |

```python
from kseb_client import KSEBClient, KSEBValidationError, KSEBTransformerNotFoundError

client = KSEBClient()

try:
    result = client.get_grid_capacity("invalid", "9895672251")
except KSEBValidationError as e:
    print(f"Invalid input: {e}")
except KSEBTransformerNotFoundError as e:
    print(f"Transformer not found: {e}")
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
result = client.get_grid_capacity("1145657015077", "9895672251")
```

Output:
```
DEBUG:kseb_client.client:KSEBClient initialized: timeout=15s, retries=3, backoff=0.3, cache_ttl=900s
DEBUG:kseb_client.session:GET https://kseb.in/knowursectiondetail
INFO:kseb_client.section:Section details retrieved: Sample Section
DEBUG:kseb_client.session:GET https://old.kseb.in/billview/
DEBUG:kseb_client.session:POST https://old.kseb.in/billview/index.php
INFO:kseb_client.bill:Bill downloaded successfully (150000 bytes)
...
```

## Integration Examples

### FastAPI

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from kseb_client import KSEBClient, KSEBClientError

app = FastAPI()
client = KSEBClient()

@app.get("/grid-capacity/{consumer_no}/{mobile}")
async def get_grid_capacity(consumer_no: str, mobile: str):
    try:
        result = client.get_grid_capacity(consumer_no, mobile)
        return {
            "section": result.section.section,
            "consumer": result.bill.consumer_name,
            "transformer": result.transformer.transformer_name,
            "balance": result.transformer.balance_available
        }
    except KSEBClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Flask

```python
from flask import Flask, request, jsonify
from kseb_client import KSEBClient, KSEBClientError

app = Flask(__name__)
client = KSEBClient()

@app.route("/api/grid-capacity/<consumer_no>/<mobile>", methods=["GET"])
def get_grid_capacity(consumer_no, mobile):
    try:
        result = client.get_grid_capacity(consumer_no, mobile)
        return jsonify({
            "section": result.section.section,
            "consumer": result.bill.consumer_name,
            "balance": result.transformer.balance_available
        })
    except KSEBClientError as e:
        return {"error": str(e)}, 400
```

### CLI Tool

```python
import sys
from kseb_client import KSEBClient

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <consumer_no> <mobile>")
        sys.exit(1)

    consumer_no = sys.argv[1]
    mobile = sys.argv[2]

    with KSEBClient() as client:
        result = client.get_grid_capacity(consumer_no, mobile)
        print(f"Section: {result.section.section}")
        print(f"Consumer: {result.bill.consumer_name}")
        print(f"Available Balance: {result.transformer.balance_available} kVA")

if __name__ == "__main__":
    main()
```

### Django

```python
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from kseb_client import KSEBClient, KSEBClientError

client = KSEBClient()

@require_GET
def get_grid_capacity(request):
    consumer_no = request.GET.get("consumer_no")
    mobile = request.GET.get("mobile")

    if not consumer_no or not mobile:
        return JsonResponse({"error": "Missing parameters"}, status=400)

    try:
        result = client.get_grid_capacity(consumer_no, mobile)
        return JsonResponse({
            "section": result.section.section,
            "consumer": result.bill.consumer_name,
            "balance": result.transformer.balance_available
        })
    except KSEBClientError as e:
        return JsonResponse({"error": str(e)}, status=400)
```

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
    KSEBAuthenticationError,
    KSEBTransformerNotFoundError,
    KSEBParsingError,
    KSEBNetworkError,
    KSEBClientError
)

client = KSEBClient()

try:
    result = client.get_grid_capacity("1145657015077", "9895672251")
except KSEBValidationError as e:
    # Handle invalid input
    print(f"Invalid input: {e.message} (field: {e.field})")
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
transformers = client.get_transformers("1234")

# Bypass cache
transformers = client.get_transformers("1234", use_cache=False)

# Clear cache manually
client.clear_cache()
```

2. **Reuse Client**: Create one client instance and reuse it across your application to maintain connection pooling.

```python
# Good - reuse client
client = KSEBClient()
for consumer_no in consumer_list:
    result = client.get_grid_capacity(consumer_no, mobile)

# Avoid - creating new clients
for consumer_no in consumer_list:
    client = KSEBClient()
    result = client.get_grid_capacity(consumer_no, mobile)
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
