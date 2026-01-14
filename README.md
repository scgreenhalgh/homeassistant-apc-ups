# APC UPS Integration - Development Repository

Private development repository for the Home Assistant APC UPS SNMP integration.

**Public Release Repository:** [homeassistant-apc-ups](https://github.com/scgreenhalgh/homeassistant-apc-ups)

## Project Structure

```
ha_apc_ups_dev/
├── custom_components/
│   └── apc_ups_snmp/
│       ├── __init__.py          # Integration setup
│       ├── config_flow.py       # UI configuration
│       ├── const.py             # Constants & OIDs
│       ├── coordinator.py       # Data update coordinator
│       ├── entity.py            # Base entity class
│       ├── sensor.py            # Sensor entities
│       ├── binary_sensor.py     # Binary sensor entities
│       ├── snmp_client.py       # SNMP communication layer
│       ├── manifest.json        # Integration metadata
│       ├── strings.json         # UI strings
│       └── translations/
│           └── en.json          # English translations
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_config_flow.py      # Config flow tests
│   ├── test_coordinator.py      # Coordinator tests
│   ├── test_sensor.py           # Sensor tests
│   └── test_snmp_client.py      # SNMP client tests
├── docs/
│   └── snmp_explanation.md      # SNMP protocol documentation
├── pyproject.toml               # Project configuration
├── requirements.txt             # Runtime dependencies
└── requirements_test.txt        # Test dependencies
```

## Development Setup

### Prerequisites

- Python 3.11+
- pyenv (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/scgreenhalgh/ha_apc_ups_dev.git
cd ha_apc_ups_dev

# Create virtual environment
pyenv virtualenv 3.11.8 ha_apc_ups_dev
pyenv activate ha_apc_ups_dev

# Install dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=custom_components.apc_ups_snmp --cov-report=term-missing

# Run specific test file
pytest tests/test_sensor.py -v

# Run single test
pytest tests/test_config_flow.py::TestConfigFlow::test_form_user_step_appears -v
```

### Code Quality

```bash
# Linting
ruff check custom_components/

# Type checking
mypy custom_components/
```

## Testing with Real Hardware

```python
import asyncio
from custom_components.apc_ups_snmp.snmp_client import ApcSnmpClient
from custom_components.apc_ups_snmp.const import ApcOid, SNMP_VERSION_3

async def test():
    client = ApcSnmpClient(
        host="192.168.0.71",
        port=161,
        version=SNMP_VERSION_3,
        username="homeassistant",
        auth_protocol="SHA",
        auth_password="YOUR_AUTH_PASS",
        priv_protocol="AES",
        priv_password="YOUR_PRIV_PASS",
    )

    data = await client.async_get_all_data()
    print(f"Battery: {data.get(ApcOid.BATTERY_CAPACITY)}%")
    print(f"Load: {data.get(ApcOid.OUTPUT_LOAD)}%")
    client.close()

asyncio.run(test())
```

## Architecture

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────┐
│   AP9630    │────▶│ ApcSnmpClient│────▶│ Coordinator  │────▶│ Sensors │
│    NMC      │SNMP │             │     │              │     │         │
└─────────────┘     └─────────────┘     └──────────────┘     └─────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| SNMP Client | `snmp_client.py` | Low-level SNMP communication (v2c/v3) |
| Coordinator | `coordinator.py` | Polls UPS data at regular intervals |
| Config Flow | `config_flow.py` | UI-based setup wizard |
| Sensors | `sensor.py` | Exposes UPS metrics as HA sensors |
| Binary Sensors | `binary_sensor.py` | On battery, low battery alerts |

### SNMP OIDs

All APC PowerNet MIB OIDs are defined in `const.py`. Key OIDs:

| OID | Description |
|-----|-------------|
| `.1.3.6.1.4.1.318.1.1.1.1.1.1.0` | UPS Model |
| `.1.3.6.1.4.1.318.1.1.1.2.2.1.0` | Battery Capacity |
| `.1.3.6.1.4.1.318.1.1.1.2.2.3.0` | Runtime Remaining |
| `.1.3.6.1.4.1.318.1.1.1.4.2.3.0` | Output Load |

## Release Process

To publish a new release to the public repository:

1. Update version in `manifest.json`
2. Tag the release: `git tag v1.0.0`
3. Run release script: `./scripts/release.sh v1.0.0`

Or use GitHub Actions (automated on tag push).

## Tested Hardware

| Device | NMC | Status |
|--------|-----|--------|
| Smart-UPS 1500 | AP9630 | Working |

## Security Considerations

### SNMP Version Selection

This integration supports both SNMP v2c and SNMP v3:

- **SNMP v2c**: The community string is transmitted in **cleartext** over the network. This is acceptable for isolated/trusted networks but should be avoided if traffic crosses untrusted network segments.

- **SNMP v3** (Recommended): Provides authentication and optional encryption. Use SHA256 or higher for authentication and AES for privacy when security is important.

### Credential Storage

SNMP credentials are stored in Home Assistant's configuration database, which is encrypted at rest. Credentials are never logged.

## License

MIT License
