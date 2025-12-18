"""Tests for the APC UPS SNMP config flow."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.apc_ups_snmp.const import (
    CONF_AUTH_PASSWORD,
    CONF_AUTH_PROTOCOL,
    CONF_COMMUNITY,
    CONF_PRIV_PASSWORD,
    CONF_PRIV_PROTOCOL,
    CONF_SENSORS,
    CONF_SNMP_VERSION,
    DOMAIN,
    SNMP_VERSION_2C,
    SNMP_VERSION_3,
    ApcOid,
)
from custom_components.apc_ups_snmp.snmp_client import (
    SnmpAuthError,
    SnmpConnectionError,
    SnmpTimeoutError,
)


@pytest.fixture
def mock_snmp_data() -> dict[str, Any]:
    """Return mock SNMP data from UPS."""
    return {
        ApcOid.MODEL: "Smart-UPS 1500",
        ApcOid.NAME: "UPS_Server_Room",
        ApcOid.FIRMWARE: "UPS 09.3",
        ApcOid.SERIAL: "AS1234567890",
        ApcOid.BATTERY_STATUS: 2,
        ApcOid.BATTERY_CAPACITY: 100,
        ApcOid.BATTERY_TEMPERATURE: 25,
        ApcOid.BATTERY_RUNTIME: 27000000,
        ApcOid.BATTERY_REPLACE: 1,
        ApcOid.INPUT_VOLTAGE: 120,
        ApcOid.INPUT_FREQUENCY: 60,
        ApcOid.OUTPUT_STATUS: 2,
        ApcOid.OUTPUT_VOLTAGE: 120,
        ApcOid.OUTPUT_FREQUENCY: 60,
        ApcOid.OUTPUT_LOAD: 25,
        ApcOid.OUTPUT_CURRENT: 2,
    }


@pytest.fixture
def mock_ups_identity() -> dict:
    """Return mock UPS identity data."""
    return {
        "model": "Smart-UPS 1500",
        "name": "UPS_Server_Room",
        "firmware": "UPS 09.3",
        "serial": "AS1234567890",
    }


class TestConfigFlow:
    """Test the config flow."""

    async def test_form_user_step_appears(self, hass: HomeAssistant) -> None:
        """Test that the user step form appears."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_snmp_v2c_flow_success(
        self, hass: HomeAssistant, mock_ups_identity: dict, mock_snmp_data: dict
    ) -> None:
        """Test successful SNMP v2c configuration flow."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.apc_ups_snmp.config_flow.ApcSnmpClient"
        ) as mock_config_client_class, patch(
            "custom_components.apc_ups_snmp.coordinator.ApcSnmpClient"
        ) as mock_coord_client_class:
            # Mock for config flow
            mock_config_client = AsyncMock()
            mock_config_client.async_test_connection = AsyncMock(return_value=True)
            mock_config_client.async_get_identity = AsyncMock(return_value=mock_ups_identity)
            mock_config_client.close = MagicMock()
            mock_config_client_class.return_value = mock_config_client

            # Mock for coordinator
            mock_coord_client = MagicMock()
            mock_coord_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
            mock_coord_client.close = MagicMock()
            mock_coord_client_class.return_value = mock_coord_client

            # Step 1: Enter host and SNMP version
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_2C,
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "auth_v2c"

            # Step 2: Enter community string
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNITY: "public"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "sensors"

            # Step 3: Select sensors
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_SENSORS: ["battery_capacity", "output_load"]},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "Smart-UPS 1500"
            assert result["data"]["host"] == "192.168.1.100"
            assert result["data"][CONF_SNMP_VERSION] == SNMP_VERSION_2C
            assert result["data"][CONF_COMMUNITY] == "public"

    async def test_snmp_v3_flow_success(
        self, hass: HomeAssistant, mock_ups_identity: dict, mock_snmp_data: dict
    ) -> None:
        """Test successful SNMP v3 configuration flow."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.apc_ups_snmp.config_flow.ApcSnmpClient"
        ) as mock_config_client_class, patch(
            "custom_components.apc_ups_snmp.coordinator.ApcSnmpClient"
        ) as mock_coord_client_class:
            # Mock for config flow
            mock_config_client = AsyncMock()
            mock_config_client.async_test_connection = AsyncMock(return_value=True)
            mock_config_client.async_get_identity = AsyncMock(return_value=mock_ups_identity)
            mock_config_client.close = MagicMock()
            mock_config_client_class.return_value = mock_config_client

            # Mock for coordinator
            mock_coord_client = MagicMock()
            mock_coord_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
            mock_coord_client.close = MagicMock()
            mock_coord_client_class.return_value = mock_coord_client

            # Step 1: Enter host and SNMP version
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_3,
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "auth_v3"

            # Step 2: Enter v3 credentials
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "username": "admin",
                    CONF_AUTH_PROTOCOL: "SHA",
                    CONF_AUTH_PASSWORD: "authpass123",
                    CONF_PRIV_PROTOCOL: "AES",
                    CONF_PRIV_PASSWORD: "privpass123",
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "sensors"

            # Step 3: Select sensors
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_SENSORS: ["battery_capacity"]},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["data"][CONF_SNMP_VERSION] == SNMP_VERSION_3
            assert result["data"]["username"] == "admin"

    async def test_invalid_host(self, hass: HomeAssistant) -> None:
        """Test handling of invalid host."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.apc_ups_snmp.config_flow.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_test_connection = AsyncMock(
                side_effect=SnmpConnectionError("Host unreachable")
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            # Enter host and SNMP version
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_2C,
                },
            )

            # Enter community string - should fail connection test
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNITY: "public"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "auth_v2c"
            assert result["errors"]["base"] == "cannot_connect"

    async def test_connection_timeout(self, hass: HomeAssistant) -> None:
        """Test handling of connection timeout."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.apc_ups_snmp.config_flow.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_test_connection = AsyncMock(
                side_effect=SnmpTimeoutError("Connection timed out")
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_2C,
                },
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNITY: "public"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "timeout"

    async def test_auth_failure_v2c(self, hass: HomeAssistant) -> None:
        """Test handling of SNMP v2c authentication failure."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.apc_ups_snmp.config_flow.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_test_connection = AsyncMock(
                side_effect=SnmpAuthError("Wrong community string")
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_2C,
                },
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNITY: "wrongcommunity"},
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "invalid_auth"

    async def test_auth_failure_v3(self, hass: HomeAssistant) -> None:
        """Test handling of SNMP v3 authentication failure."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.apc_ups_snmp.config_flow.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.async_test_connection = AsyncMock(
                side_effect=SnmpAuthError("Authentication failed")
            )
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_3,
                },
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "username": "admin",
                    CONF_AUTH_PROTOCOL: "SHA",
                    CONF_AUTH_PASSWORD: "wrongpassword",
                    CONF_PRIV_PROTOCOL: "AES",
                    CONF_PRIV_PASSWORD: "wrongpassword",
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "invalid_auth"

    async def test_unique_id_prevents_duplicate(
        self, hass: HomeAssistant, mock_ups_identity: dict, mock_snmp_data: dict
    ) -> None:
        """Test that duplicate UPS entries are prevented."""
        # Create first entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.apc_ups_snmp.config_flow.ApcSnmpClient"
        ) as mock_config_client_class, patch(
            "custom_components.apc_ups_snmp.coordinator.ApcSnmpClient"
        ) as mock_coord_client_class:
            # Mock for config flow
            mock_config_client = AsyncMock()
            mock_config_client.async_test_connection = AsyncMock(return_value=True)
            mock_config_client.async_get_identity = AsyncMock(return_value=mock_ups_identity)
            mock_config_client.close = MagicMock()
            mock_config_client_class.return_value = mock_config_client

            # Mock for coordinator
            mock_coord_client = MagicMock()
            mock_coord_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
            mock_coord_client.close = MagicMock()
            mock_coord_client_class.return_value = mock_coord_client

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_2C,
                },
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_COMMUNITY: "public"},
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_SENSORS: ["battery_capacity"]},
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY

            # Try to create duplicate entry (still within the same patch context)
            result2 = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {
                    "host": "192.168.1.100",
                    "port": 161,
                    CONF_SNMP_VERSION: SNMP_VERSION_2C,
                },
            )

            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {CONF_COMMUNITY: "public"},
            )

            # Should abort due to duplicate unique ID
            assert result2["type"] == FlowResultType.ABORT
            assert result2["reason"] == "already_configured"


class TestOptionsFlow:
    """Test the options flow."""

    @patch("custom_components.apc_ups_snmp.coordinator.ApcSnmpClient")
    @patch("custom_components.apc_ups_snmp.config_flow.ApcSnmpClient")
    async def test_options_flow_update_sensors(
        self,
        mock_config_client_class,
        mock_coord_client_class,
        hass: HomeAssistant,
        mock_ups_identity: dict,
        mock_snmp_data: dict,
    ) -> None:
        """Test updating sensor selection via options flow."""
        # Mock for config flow
        mock_config_client = AsyncMock()
        mock_config_client.async_test_connection = AsyncMock(return_value=True)
        mock_config_client.async_get_identity = AsyncMock(return_value=mock_ups_identity)
        mock_config_client.close = MagicMock()
        mock_config_client_class.return_value = mock_config_client

        # Mock for coordinator
        mock_coord_client = MagicMock()
        mock_coord_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
        mock_coord_client.close = MagicMock()
        mock_coord_client_class.return_value = mock_coord_client

        # First create a config entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "192.168.1.100",
                "port": 161,
                CONF_SNMP_VERSION: SNMP_VERSION_2C,
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_COMMUNITY: "public"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_SENSORS: ["battery_capacity"]},
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        entry = result["result"]

        # Now test options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SENSORS: ["battery_capacity", "output_load", "input_voltage"]},
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert "battery_capacity" in result["data"][CONF_SENSORS]
        assert "output_load" in result["data"][CONF_SENSORS]
        assert "input_voltage" in result["data"][CONF_SENSORS]

        # Wait for reload to complete within the patch context
        await hass.async_block_till_done()
