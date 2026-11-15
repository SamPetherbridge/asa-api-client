# Installation

## Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager:

```bash
uv add asa-api-client
```

With optional extras:

```bash
# DataFrame export (report.to_dataframe())
uv add "asa-api-client[pandas]"

# Command-line toolkit (asa analyze / asa smoke)
uv add "asa-api-client[cli]"
```

## Using pip

```bash
pip install asa-api-client
```

With optional extras:

```bash
pip install "asa-api-client[pandas]"
pip install "asa-api-client[cli]"
```

## Requirements

- Python 3.13+
- Valid Apple Ads API credentials

## Dependencies

Core runtime dependencies:

- `httpx` — HTTP client with sync and async transports
- `pydantic` — Request/response validation
- `pydantic-settings` — Environment and `.env` configuration
- `pyjwt[crypto]` — ES256 client-secret JWT signing

Optional extras:

- `pandas` — `to_dataframe()` export on report responses
- `cli` — `typer`, `rich`, `pandas`, and `xlsxwriter` for `asa analyze` and `asa smoke`
