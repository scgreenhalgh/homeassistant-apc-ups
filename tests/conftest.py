"""Fixtures for APC UPS SNMP integration tests."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.apc_ups_snmp.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,  # noqa: ARG001
) -> Generator[None, None, None]:
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_snmp_response() -> dict[str, Any]:
    """Return a mock SNMP response for a typical APC UPS."""
    return {
        # Identity
        ".1.3.6.1.4.1.318.1.1.1.1.1.1.0": "Smart-UPS 1500",
        ".1.3.6.1.4.1.318.1.1.1.1.1.2.0": "UPS_Server_Room",
        ".1.3.6.1.4.1.318.1.1.1.1.2.1.0": "UPS 09.3",
        ".1.3.6.1.4.1.318.1.1.1.1.2.2.0": "AS1234567890",
        # Battery
        ".1.3.6.1.4.1.318.1.1.1.2.1.1.0": 2,  # batteryNormal
        ".1.3.6.1.4.1.318.1.1.1.2.2.1.0": 100,  # capacity %
        ".1.3.6.1.4.1.318.1.1.1.2.2.2.0": 25,  # temperature C
        ".1.3.6.1.4.1.318.1.1.1.2.2.3.0": 27000000,  # runtime timeticks (45 min)
        ".1.3.6.1.4.1.318.1.1.1.2.2.4.0": 1,  # noBatteryNeedsReplacing
        # Input
        ".1.3.6.1.4.1.318.1.1.1.3.2.1.0": 120,  # input voltage
        ".1.3.6.1.4.1.318.1.1.1.3.2.4.0": 60,  # input frequency
        # Output
        ".1.3.6.1.4.1.318.1.1.1.4.1.1.0": 2,  # onLine
        ".1.3.6.1.4.1.318.1.1.1.4.2.1.0": 120,  # output voltage
        ".1.3.6.1.4.1.318.1.1.1.4.2.2.0": 60,  # output frequency
        ".1.3.6.1.4.1.318.1.1.1.4.2.3.0": 25,  # output load %
        ".1.3.6.1.4.1.318.1.1.1.4.2.4.0": 2,  # output current
    }


@pytest.fixture
def mock_snmp_client() -> Generator[MagicMock, None, None]:
    """Create a mock SNMP client."""
    with patch(
        "custom_components.apc_ups_snmp.snmp_client.ApcSnmpClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.async_get = AsyncMock()
        mock_client.async_get_multiple = AsyncMock()
        mock_client.async_test_connection = AsyncMock(return_value=True)
        mock_client.close = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_config_entry_data_v2c() -> dict[str, Any]:
    """Return mock config entry data for SNMP v2c."""
    return {
        "host": "192.168.1.100",
        "port": 161,
        "snmp_version": "v2c",
        "community": "public",
        "name": "Server Room UPS",
    }


@pytest.fixture
def mock_config_entry_data_v3() -> dict[str, Any]:
    """Return mock config entry data for SNMP v3."""
    return {
        "host": "192.168.1.100",
        "port": 161,
        "snmp_version": "v3",
        "username": "admin",
        "auth_protocol": "SHA",
        "auth_password": "authpass123",
        "priv_protocol": "AES",
        "priv_password": "privpass123",
        "name": "Server Room UPS",
    }
