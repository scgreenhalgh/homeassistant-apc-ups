# Home Assistant Testing Environment for Custom Integration Development

This document provides a comprehensive guide to setting up a local Home Assistant test environment for developing and testing custom integrations. The approach uses Docker to create an isolated, reproducible testing environment that can be quickly started, stopped, and reset.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Directory Structure](#directory-structure)
4. [Docker Compose Configuration](#docker-compose-configuration)
5. [Home Assistant Configuration](#home-assistant-configuration)
6. [Management Script](#management-script)
7. [Environment Variables](#environment-variables)
8. [Usage Guide](#usage-guide)
9. [Testing Workflow](#testing-workflow)
10. [Automated Integration Setup via REST API](#automated-integration-setup-via-rest-api)
11. [Debugging](#debugging)
12. [Common Issues and Solutions](#common-issues-and-solutions)
13. [Direct Component Testing](#direct-component-testing)
14. [Unit Testing](#unit-testing)
15. [Best Practices](#best-practices)

---

## Overview

### Why Use Docker for Testing?

1. **Isolation**: Test environment is completely separate from production
2. **Reproducibility**: Start with a clean slate every time
3. **Speed**: No need to install Home Assistant dependencies on your machine
4. **Real Environment**: Tests run in the same environment as production
5. **Easy Cleanup**: Delete and recreate in seconds

### Testing Strategy

This setup supports three levels of testing:

| Level | Description | Speed | Fidelity |
|-------|-------------|-------|----------|
| **Unit Tests** | pytest with mocked Home Assistant | Fast | Lower |
| **Direct Testing** | Python script testing components directly | Fast | Medium |
| **Integration Testing** | Full Home Assistant in Docker | Slow | Highest |

---

## Prerequisites

### Required Software

1. **Docker Desktop** (or Docker Engine on Linux)
   - macOS: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Linux: `sudo apt install docker.io docker-compose` or equivalent

2. **Python 3.11+** (for unit tests and direct testing)
   ```bash
   python3 --version  # Should be 3.11 or higher
   ```

3. **curl** (for API testing - usually pre-installed)
   ```bash
   curl --version
   ```

4. **jq** (optional, for JSON parsing in scripts)
   ```bash
   # macOS
   brew install jq

   # Ubuntu/Debian
   sudo apt install jq
   ```

### Network Requirements

- Port 8123 must be available on localhost
- If testing with real hardware (like a UPS), ensure Docker can reach your local network
- On macOS, Docker runs in a VM so `network_mode: host` doesn't work - use port mapping instead

---

## Directory Structure

```
your-integration/
├── custom_components/
│   └── your_integration/          # Your integration code
│       ├── __init__.py
│       ├── config_flow.py
│       ├── manifest.json
│       └── ...
├── tests/                         # Unit tests
│   ├── conftest.py
│   └── test_*.py
├── scripts/
│   ├── test_real_hardware.py      # Direct component testing
│   └── ha_test_env/               # Docker test environment
│       ├── docker-compose.yml
│       ├── manage.sh
│       └── config/
│           └── configuration.yaml
├── .env                           # Credentials (git-ignored)
├── .gitignore
└── docs/
    └── HOME_ASSISTANT_TESTING_ENVIRONMENT.md
```

---

## Docker Compose Configuration

Create `scripts/ha_test_env/docker-compose.yml`:

```yaml
services:
  homeassistant:
    container_name: ha_test
    image: ghcr.io/home-assistant/home-assistant:stable
    volumes:
      # Main config directory
      - ./config:/config
      # Mount the custom integration directly (read-only)
      - ../../custom_components/your_integration:/config/custom_components/your_integration:ro
    environment:
      - TZ=Your/Timezone  # e.g., Australia/Sydney, America/New_York
    # Use port mapping (host network doesn't work on macOS Docker)
    ports:
      - "8123:8123"
    restart: unless-stopped
```

### Key Configuration Points

1. **Volume Mounts**:
   - `./config:/config` - Persistent HA configuration
   - `../../custom_components/...` - Your integration code (read-only mount)

2. **Port Mapping**:
   - Use `ports:` instead of `network_mode: host` for macOS compatibility
   - Host network mode only works on Linux

3. **Image Selection**:
   - `stable` - Latest stable release
   - `2024.12` - Specific version (recommended for reproducibility)
   - `dev` - Development version (for testing against upcoming changes)

---

## Home Assistant Configuration

Create `scripts/ha_test_env/config/configuration.yaml`:

```yaml
# Home Assistant Test Configuration
# Minimal config for testing custom integrations

homeassistant:
  name: HA Test Instance
  unit_system: metric
  time_zone: Your/Timezone
  # Enable trusted networks for easier API access
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 127.0.0.1
        - ::1
        - 192.168.0.0/24      # Adjust for your network
        - 172.16.0.0/12       # Docker networks
      allow_bypass_login: true
    - type: homeassistant      # Fallback to standard auth

# Debug logging for your integration
logger:
  default: info
  logs:
    custom_components.your_integration: debug
    # Add other components as needed
    # pysnmp: warning

# Enable the REST API for automation
api:

# HTTP configuration
http:
  server_port: 8123
  cors_allowed_origins:
    - "*"  # Allow all origins for testing (not for production!)

# Enable frontend (optional, for manual testing)
frontend:

# Enable config panel (optional)
config:
```

### Configuration Explained

1. **Trusted Networks**: Allows API access without authentication from specified networks - essential for automated testing

2. **Logger Settings**: Debug logging for your integration helps identify issues

3. **CORS Settings**: Allows API access from any origin - useful for testing from different tools

---

## Management Script

Create `scripts/ha_test_env/manage.sh`:

```bash
#!/bin/bash
# Home Assistant Test Environment Management Script
#
# Usage:
#   ./manage.sh start     - Start HA test instance
#   ./manage.sh stop      - Stop HA test instance
#   ./manage.sh restart   - Restart HA test instance
#   ./manage.sh logs      - Show HA logs (follow mode)
#   ./manage.sh status    - Check if HA is running
#   ./manage.sh shell     - Open shell in HA container
#   ./manage.sh clean     - Stop and remove all data (fresh start)
#   ./manage.sh setup     - Configure integration via API
#   ./manage.sh test      - Run full test cycle

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env file from project root if it exists
ENV_FILE="$SCRIPT_DIR/../../.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Configuration
HA_URL="http://localhost:8123"
CONTAINER_NAME="ha_test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_ha() {
    log_info "Waiting for Home Assistant to start..."
    local max_attempts=60
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "$HA_URL/api/" > /dev/null 2>&1; then
            log_info "Home Assistant is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo ""
    log_error "Home Assistant did not start within expected time"
    return 1
}

cmd_start() {
    log_info "Starting Home Assistant test instance..."

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    # Create directories if needed
    mkdir -p config/custom_components

    docker compose up -d
    wait_for_ha

    log_info "Home Assistant is running at $HA_URL"
    log_info "To add integrations, run: ./manage.sh setup"
}

cmd_stop() {
    log_info "Stopping Home Assistant test instance..."
    docker compose down
    log_info "Home Assistant stopped"
}

cmd_restart() {
    log_info "Restarting Home Assistant test instance..."
    docker compose restart
    wait_for_ha
    log_info "Home Assistant restarted"
}

cmd_logs() {
    log_info "Showing Home Assistant logs (Ctrl+C to exit)..."
    docker compose logs -f homeassistant
}

cmd_status() {
    if docker compose ps | grep -q "running"; then
        log_info "Home Assistant is running"
        docker compose ps

        if curl -s "$HA_URL/api/" > /dev/null 2>&1; then
            log_info "API is responding at $HA_URL"
        else
            log_warn "API is not responding yet"
        fi
    else
        log_warn "Home Assistant is not running"
    fi
}

cmd_shell() {
    log_info "Opening shell in Home Assistant container..."
    docker exec -it $CONTAINER_NAME /bin/bash
}

cmd_clean() {
    log_warn "This will remove all Home Assistant data. Are you sure? (y/N)"
    read -r response
    if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
        log_info "Stopping and cleaning up..."
        docker compose down -v 2>/dev/null || true
        rm -rf config/.storage config/home-assistant_v2.db config/home-assistant.log*
        log_info "Cleanup complete. Run './manage.sh start' for a fresh instance."
    else
        log_info "Cancelled"
    fi
}

cmd_setup() {
    log_info "Setting up integration via REST API..."

    # Check if HA is running
    if ! curl -s "$HA_URL/api/" > /dev/null 2>&1; then
        log_error "Home Assistant is not running. Start it first with: ./manage.sh start"
        exit 1
    fi

    # Add your integration setup logic here
    # See "Automated Integration Setup via REST API" section
    log_info "Setup complete"
}

cmd_test() {
    log_info "Running full test cycle..."

    cmd_start
    sleep 5
    cmd_setup

    log_info "Waiting for data collection..."
    sleep 30

    # Check for errors
    log_info "Checking logs for errors..."
    if docker compose logs homeassistant 2>&1 | grep -iE "error|exception" | grep -i "your_integration"; then
        log_error "Found errors in logs"
    else
        log_info "No obvious errors found"
    fi

    log_info "Test cycle complete. HA running at $HA_URL"
}

# Main command handler
case "${1:-}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    logs)    cmd_logs ;;
    status)  cmd_status ;;
    shell)   cmd_shell ;;
    clean)   cmd_clean ;;
    setup)   cmd_setup ;;
    test)    cmd_test ;;
    *)
        echo "Home Assistant Test Environment Manager"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  start     Start Home Assistant test instance"
        echo "  stop      Stop Home Assistant test instance"
        echo "  restart   Restart Home Assistant test instance"
        echo "  logs      Show Home Assistant logs (follow mode)"
        echo "  status    Check if Home Assistant is running"
        echo "  shell     Open shell in Home Assistant container"
        echo "  clean     Stop and remove all data (fresh start)"
        echo "  setup     Configure integration via API"
        echo "  test      Run full test cycle"
        ;;
esac
```

Make the script executable:
```bash
chmod +x scripts/ha_test_env/manage.sh
```

---

## Environment Variables

Create a `.env` file in your project root for credentials and configuration:

```bash
# .env - DO NOT COMMIT THIS FILE

# Example: UPS Configuration for SNMP integration
UPS1_HOST=192.168.0.71
UPS1_PORT=161
UPS1_SNMP_VERSION=v3
UPS1_USERNAME=your_username
UPS1_AUTH_PROTOCOL=SHA
UPS1_AUTH_PASSWORD=your_auth_password
UPS1_PRIV_PROTOCOL=AES
UPS1_PRIV_PASSWORD=your_priv_password

# Example: For SNMP v2c
# UPS1_SNMP_VERSION=v2c
# UPS1_COMMUNITY=public

# Add other integration-specific variables as needed
```

**Important**: Add `.env` to your `.gitignore`:
```gitignore
# Credentials
.env
.secrets/
credentials.json
```

---

## Usage Guide

### Starting the Environment

```bash
cd scripts/ha_test_env
./manage.sh start
```

This will:
1. Start Docker containers
2. Wait for Home Assistant to be ready
3. Display the URL (http://localhost:8123)

### Accessing Home Assistant

1. **Web UI**: Open http://localhost:8123 in your browser
2. **First-time Setup**: If prompted, complete the onboarding wizard
3. **With Trusted Networks**: You may be automatically logged in

### Adding Your Integration

**Method 1: Via Web UI**
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for your integration
4. Follow the config flow

**Method 2: Via REST API** (see next section)

### Viewing Logs

```bash
# Follow logs in real-time
./manage.sh logs

# Filter for your integration
./manage.sh logs | grep your_integration

# View logs inside container
./manage.sh shell
cat /config/home-assistant.log
```

### Stopping the Environment

```bash
./manage.sh stop
```

### Fresh Start

```bash
./manage.sh clean
./manage.sh start
```

---

## Automated Integration Setup via REST API

### Understanding Config Flows

Home Assistant uses "config flows" to set up integrations. The flow is a multi-step process:

1. **Initialize flow** → Get flow_id
2. **Submit step data** → Get next step or completion
3. **Repeat** until flow completes

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/config/config_entries/flow` | POST | Start a config flow |
| `/api/config/config_entries/flow/{flow_id}` | POST | Submit step data |
| `/api/states` | GET | Get all entity states |
| `/api/states/{entity_id}` | GET | Get specific entity state |

### Example: Multi-Step Config Flow

```bash
#!/bin/bash
# Example: Setting up an integration with multiple steps

HA_URL="http://localhost:8123"

# Step 1: Initialize the config flow
echo "Starting config flow..."
FLOW_RESULT=$(curl -s -X POST "$HA_URL/api/config/config_entries/flow" \
    -H "Content-Type: application/json" \
    -d '{"handler": "your_integration"}')

FLOW_ID=$(echo "$FLOW_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('flow_id', ''))")
echo "Flow ID: $FLOW_ID"

# Step 2: Submit first step data (e.g., host/port)
echo "Submitting host configuration..."
STEP1_RESULT=$(curl -s -X POST "$HA_URL/api/config/config_entries/flow/$FLOW_ID" \
    -H "Content-Type: application/json" \
    -d '{
        "host": "192.168.0.71",
        "port": 161
    }')

# Check what step we're on now
STEP_ID=$(echo "$STEP1_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('step_id', ''))")
echo "Next step: $STEP_ID"

# Step 3: Submit credentials if needed
if [ "$STEP_ID" = "auth" ]; then
    echo "Submitting credentials..."
    STEP2_RESULT=$(curl -s -X POST "$HA_URL/api/config/config_entries/flow/$FLOW_ID" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "your_user",
            "password": "your_pass"
        }')
fi

# Check result
RESULT_TYPE=$(echo "${STEP2_RESULT:-$STEP1_RESULT}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type', ''))")

if [ "$RESULT_TYPE" = "create_entry" ]; then
    echo "Integration configured successfully!"
else
    echo "Setup result: $RESULT_TYPE"
fi
```

### Verifying Sensor Data

```bash
# Get all states
curl -s "$HA_URL/api/states" | python3 -m json.tool

# Get specific sensor
curl -s "$HA_URL/api/states/sensor.your_sensor_name" | python3 -m json.tool

# Filter for your integration's entities
curl -s "$HA_URL/api/states" | python3 -c "
import sys, json
states = json.load(sys.stdin)
for state in states:
    if 'your_integration' in state['entity_id']:
        print(f\"{state['entity_id']}: {state['state']}\")
"
```

---

## Debugging

### Enable Debug Logging

In `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.your_integration: debug
    homeassistant.config_entries: debug
    homeassistant.setup: debug
```

### Common Debug Commands

```bash
# View real-time logs
docker compose logs -f homeassistant

# Filter for your integration
docker compose logs homeassistant 2>&1 | grep your_integration

# Check for blocking I/O warnings
docker compose logs homeassistant 2>&1 | grep -i "blocking"

# Check for errors
docker compose logs homeassistant 2>&1 | grep -iE "error|exception|traceback"

# Access container shell
docker exec -it ha_test /bin/bash

# Inside container:
cat /config/home-assistant.log | tail -100
pip list | grep your-dependency
python3 -c "import your_module; print(your_module.__version__)"
```

### Inspecting State

```bash
# Inside container, use Python
docker exec -it ha_test python3 << 'EOF'
import json
with open('/config/.storage/core.config_entries') as f:
    data = json.load(f)
    for entry in data['data']['entries']:
        print(f"{entry['domain']}: {entry['title']}")
EOF
```

---

## Common Issues and Solutions

### Issue: "network_mode: host" Not Working (macOS)

**Symptom**: Container can't reach local network devices

**Solution**: Use port mapping instead:
```yaml
# Instead of:
# network_mode: host

# Use:
ports:
  - "8123:8123"
```

For accessing local network devices, ensure your network allows Docker container access to the host's network.

### Issue: Integration Not Appearing

**Symptom**: Integration doesn't show in Add Integration list

**Checklist**:
1. Check volume mount path in docker-compose.yml
2. Verify manifest.json is valid JSON
3. Check container logs for import errors
4. Restart HA after code changes

```bash
# Check if files are mounted correctly
docker exec ha_test ls -la /config/custom_components/your_integration/

# Check for Python import errors
docker compose logs homeassistant 2>&1 | grep -i "import\|module"
```

### Issue: Blocking I/O Warnings

**Symptom**: `Detected blocking call to ... in the event loop`

**Solution**: Wrap blocking operations in `run_in_executor`:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def async_blocking_operation():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, blocking_function)
    return result
```

### Issue: Config Flow Schema Serialization Error

**Symptom**: `ValueError: Unable to convert schema: <class 'list'>`

**Solution**: Use SelectSelector instead of raw voluptuous validators:
```python
# Instead of:
vol.Required("items"): [vol.In(["a", "b", "c"])]

# Use:
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

vol.Required("items"): SelectSelector(
    SelectSelectorConfig(
        options=[{"value": "a", "label": "Option A"}, ...],
        multiple=True,
        mode="list",
    )
)
```

### Issue: Changes Not Reflecting

**Symptom**: Code changes don't appear in running HA

**Solution**: The volume mount is read-only. You need to restart:
```bash
./manage.sh restart
```

For faster iteration, consider using the direct testing approach (see next section).

---

## Direct Component Testing

For faster iteration, test your components directly without Home Assistant:

Create `scripts/test_direct.py`:

```python
#!/usr/bin/env python3
"""Direct testing of integration components without Home Assistant."""

import asyncio
import os
import sys
from pathlib import Path

# Add custom_components to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import your component
from custom_components.your_integration.client import YourClient


async def main():
    """Run direct tests."""
    print("=" * 60)
    print("Direct Component Test")
    print("=" * 60)

    # Create client with config from environment
    client = YourClient(
        host=os.getenv("HOST"),
        username=os.getenv("USERNAME"),
        password=os.getenv("PASSWORD"),
    )

    # Test connection
    print("\nTesting connection...")
    try:
        result = await client.async_test_connection()
        print(f"Connection: {'SUCCESS' if result else 'FAILED'}")
    except Exception as e:
        print(f"Connection ERROR: {e}")

    # Test data retrieval
    print("\nFetching data...")
    try:
        data = await client.async_get_data()
        for key, value in data.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"Data ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python scripts/test_direct.py
```

---

## Unit Testing

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_config_flow.py  # Config flow tests
├── test_sensor.py       # Sensor tests
├── test_client.py       # Client/API tests
└── test_coordinator.py  # Coordinator tests
```

### Example conftest.py

```python
"""Shared fixtures for tests."""

import pytest
from unittest.mock import AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.your_integration.const import DOMAIN


@pytest.fixture
def mock_client():
    """Create a mock client."""
    with patch("custom_components.your_integration.YourClient") as mock:
        client = mock.return_value
        client.async_test_connection = AsyncMock(return_value=True)
        client.async_get_data = AsyncMock(return_value={"key": "value"})
        yield client


@pytest.fixture
async def hass():
    """Create a Home Assistant instance for testing."""
    hass = HomeAssistant()
    hass.config.components.add("homeassistant")
    yield hass
    await hass.async_stop()
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=custom_components/your_integration

# Run specific test
pytest tests/test_config_flow.py -v -k "test_user_form"
```

---

## Best Practices

### 1. Version Pin Docker Images

```yaml
# Specific version for reproducibility
image: ghcr.io/home-assistant/home-assistant:2024.12

# Not:
# image: ghcr.io/home-assistant/home-assistant:stable
```

### 2. Use .gitignore Properly

```gitignore
# HA runtime files
scripts/ha_test_env/config/.storage/
scripts/ha_test_env/config/.HA_VERSION
scripts/ha_test_env/config/.ha_run.lock
scripts/ha_test_env/config/home-assistant.log*
scripts/ha_test_env/config/blueprints/

# Credentials
.env
.secrets/
```

### 3. Test at Multiple Levels

1. **Unit tests** (fast, run often)
2. **Direct component tests** (medium, for integration logic)
3. **Full HA tests** (slow, for final verification)

### 4. Document Your Setup

Include a README in your test environment directory explaining:
- How to set up credentials
- How to run tests
- Common troubleshooting steps

### 5. Use CI/CD

Set up GitHub Actions to run your tests automatically:

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements_test.txt
      - run: pytest tests/ -v
```

---

## Summary

This testing environment provides:

1. **Docker-based HA instance** for realistic testing
2. **Management scripts** for easy control
3. **REST API automation** for config flow testing
4. **Direct testing scripts** for fast iteration
5. **Unit test framework** for comprehensive coverage

The key is to use the right level of testing for each situation:
- Quick changes → Unit tests or direct testing
- Config flow changes → Docker environment with API
- Final verification → Full Docker environment with manual testing

Happy testing!
