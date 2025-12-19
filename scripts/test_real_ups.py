#!/usr/bin/env python3
"""Test script for SNMP client with real UPS hardware.

This script tests the SNMP client directly without Home Assistant,
allowing us to verify:
1. Connection to real UPS works
2. SNMP v3 authentication works
3. Data retrieval works
4. The blocking I/O fix works correctly

Usage:
    python scripts/test_real_ups.py

Environment variables (or use .env file):
    UPS1_HOST, UPS1_PORT, UPS1_SNMP_VERSION, UPS1_USERNAME,
    UPS1_AUTH_PROTOCOL, UPS1_AUTH_PASSWORD, UPS1_PRIV_PROTOCOL, UPS1_PRIV_PASSWORD
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add the custom_components to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    print(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

from custom_components.apc_ups_snmp.snmp_client import (
    ApcSnmpClient,
    SnmpAuthError,
    SnmpConnectionError,
    SnmpTimeoutError,
)
from custom_components.apc_ups_snmp.const import ApcOid


def get_config():
    """Get UPS configuration from environment variables."""
    return {
        "host": os.environ.get("UPS1_HOST", "192.168.0.71"),
        "port": int(os.environ.get("UPS1_PORT", "161")),
        "version": os.environ.get("UPS1_SNMP_VERSION", "v3"),
        "username": os.environ.get("UPS1_USERNAME"),
        "auth_protocol": os.environ.get("UPS1_AUTH_PROTOCOL"),
        "auth_password": os.environ.get("UPS1_AUTH_PASSWORD"),
        "priv_protocol": os.environ.get("UPS1_PRIV_PROTOCOL"),
        "priv_password": os.environ.get("UPS1_PRIV_PASSWORD"),
    }


async def test_connection(client: ApcSnmpClient) -> bool:
    """Test basic connection to the UPS."""
    print("\n" + "=" * 60)
    print("TEST: Basic Connection")
    print("=" * 60)

    start = time.time()
    try:
        result = await client.async_test_connection()
        elapsed = time.time() - start
        print(f"  Result: {'SUCCESS' if result else 'FAILED'}")
        print(f"  Time: {elapsed:.3f}s")
        return result
    except SnmpTimeoutError as e:
        print(f"  TIMEOUT: {e}")
        return False
    except SnmpAuthError as e:
        print(f"  AUTH ERROR: {e}")
        return False
    except SnmpConnectionError as e:
        print(f"  CONNECTION ERROR: {e}")
        return False
    except Exception as e:
        print(f"  UNEXPECTED ERROR: {type(e).__name__}: {e}")
        return False


async def test_identity(client: ApcSnmpClient) -> dict:
    """Test getting UPS identity information."""
    print("\n" + "=" * 60)
    print("TEST: UPS Identity")
    print("=" * 60)

    start = time.time()
    try:
        identity = await client.async_get_identity()
        elapsed = time.time() - start

        print(f"  Model:    {identity.get('model', 'N/A')}")
        print(f"  Name:     {identity.get('name', 'N/A')}")
        print(f"  Firmware: {identity.get('firmware', 'N/A')}")
        print(f"  Serial:   {identity.get('serial', 'N/A')}")
        print(f"  Time: {elapsed:.3f}s")
        return identity
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return {}


async def test_all_sensors(client: ApcSnmpClient) -> dict:
    """Test getting all sensor data."""
    print("\n" + "=" * 60)
    print("TEST: All Sensor Data")
    print("=" * 60)

    start = time.time()
    try:
        data = await client.async_get_all_data()
        elapsed = time.time() - start

        # Map OIDs to friendly names
        oid_names = {
            ApcOid.BATTERY_CAPACITY: "Battery Capacity",
            ApcOid.BATTERY_TEMPERATURE: "Battery Temperature",
            ApcOid.BATTERY_RUNTIME: "Battery Runtime (ticks)",
            ApcOid.BATTERY_STATUS: "Battery Status",
            ApcOid.BATTERY_VOLTAGE: "Battery Voltage",
            ApcOid.INPUT_VOLTAGE: "Input Voltage",
            ApcOid.INPUT_FREQUENCY: "Input Frequency",
            ApcOid.OUTPUT_VOLTAGE: "Output Voltage",
            ApcOid.OUTPUT_FREQUENCY: "Output Frequency",
            ApcOid.OUTPUT_LOAD: "Output Load",
            ApcOid.OUTPUT_CURRENT: "Output Current",
            ApcOid.OUTPUT_STATUS: "Output Status",
        }

        for oid, name in oid_names.items():
            value = data.get(oid, "N/A")
            print(f"  {name}: {value}")

        print(f"\n  Total OIDs retrieved: {len(data)}")
        print(f"  Time: {elapsed:.3f}s")
        return data
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_blocking_io_pattern():
    """Test that the blocking I/O pattern works correctly.

    This simulates what happens in Home Assistant - we run the SNMP
    client from an existing event loop and verify it doesn't block.
    """
    print("\n" + "=" * 60)
    print("TEST: Blocking I/O Pattern")
    print("=" * 60)

    config = get_config()
    client = ApcSnmpClient(**config)

    # Run multiple concurrent requests to stress test the executor pattern
    print("  Running 3 concurrent SNMP requests...")

    start = time.time()
    try:
        results = await asyncio.gather(
            client.async_get(ApcOid.MODEL),
            client.async_get(ApcOid.BATTERY_CAPACITY),
            client.async_get(ApcOid.OUTPUT_LOAD),
            return_exceptions=True,
        )
        elapsed = time.time() - start

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"  Successful requests: {success_count}/3")
        print(f"  Results: {results}")
        print(f"  Time: {elapsed:.3f}s (should be ~same as single request if parallel)")

        return success_count == 3
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("APC UPS SNMP Client - Real Hardware Test")
    print("=" * 60)

    config = get_config()
    print(f"\nConfiguration:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Version: {config['version']}")
    print(f"  Username: {config.get('username', 'N/A')}")
    print(f"  Auth Protocol: {config.get('auth_protocol', 'N/A')}")
    print(f"  Priv Protocol: {config.get('priv_protocol', 'N/A')}")

    client = ApcSnmpClient(**config)

    # Run tests
    tests_passed = 0
    tests_total = 4

    if await test_connection(client):
        tests_passed += 1

    if await test_identity(client):
        tests_passed += 1

    if await test_all_sensors(client):
        tests_passed += 1

    if await test_blocking_io_pattern():
        tests_passed += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Tests passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print("\n  All tests PASSED! The SNMP client is working correctly.")
        return 0
    else:
        print(f"\n  {tests_total - tests_passed} test(s) FAILED.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
