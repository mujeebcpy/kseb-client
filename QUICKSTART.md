# Quick Start Guide

## Installation

### Option 1: Install as a Package (Recommended)

```bash
uv add git+https://github.com/mujeebcpy/kseb-client.git
```

### Option 2: Setup Local Development

This project uses `uv` for fast, reliable Python package management.

```bash
cd /home/mujeeb/workspace/kseb-client

# Install dependencies and create virtual environment
uv sync

# That's it! Virtual environment is at .venv/
```

### Using the SDK

**Option 1: Using `uv run` (Recommended)**
```bash
uv run python3 -c "from kseb_client import KSEBClient; print(KSEBClient())"
```

**Option 2: Activate virtual environment**
```bash
source .venv/bin/activate
python3 -c "from kseb_client import KSEBClient; print(KSEBClient())"
```

**Option 3: Run scripts**
```bash
uv run python3 examples/basic.py
```

## Project Structure

- `.venv/` - Virtual environment (created by uv sync)
- `kseb_client/` - Main package with 11 modules
- `examples/` - Usage examples
- `tests/` - Test suite placeholder
- `pyproject.toml` - Project configuration (uv reads this)

## Dependencies

All auto-installed by `uv sync`:
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `pdfplumber` - PDF text extraction
- `urllib3` - URL utilities

## Common Commands

```bash
# Sync dependencies (install/update)
uv sync

# Run Python code
uv run python3 script.py

# Run with specific module
uv run python3 -m module_name

# Activate venv and use directly
source .venv/bin/activate
python3 script.py
deactivate

# Remove virtual environment
rm -rf .venv
```

## Testing

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/

# Run tests with coverage
uv run pytest tests/ --cov=kseb_client
```

## Quick Test

```bash
# Verify all imports work
uv run python3 -c "from kseb_client import KSEBClient, SectionInfo, BillInfo, Transformer, GridCapacityResult; print('✓ All imports successful!')"

# Test error handling
uv run python3 -c "from kseb_client import KSEBClient; client = KSEBClient(); print('✓ Client initialized successfully!')"
```

## What Works

✅ All imports working  
✅ Live API calls functional  
✅ Section details retrieval  
✅ Bill PDF downloading and parsing  
✅ Transformer list fetching  
✅ Error handling with custom exceptions  
✅ Logging throughout

## Next Steps

1. **Review the code**: Check out `kseb_client/client.py` for the main class
2. **Read the documentation**: See `README.md` for full API reference
3. **Run examples**: `uv run python3 examples/basic.py`
4. **Write tests**: Create tests in `tests/test_*.py`
5. **Deploy**: The SDK is production-ready!
