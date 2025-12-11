# Installation

## Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager:

```bash
uv add asa-api-client
```

With pandas support for DataFrame exports:

```bash
uv add "asa-api-client[pandas]"
```

## Using pip

```bash
pip install asa-api-client
```

With pandas support:

```bash
pip install "asa-api-client[pandas]"
```

## Requirements

- Python 3.13+
- Valid Apple Search Ads API credentials

## Dependencies

The package has minimal dependencies:

- `httpx` - HTTP client with async support
- `pydantic` - Data validation
- `pydantic-settings` - Settings management
- `pyjwt[crypto]` - JWT authentication

Optional:

- `pandas` - DataFrame export support
