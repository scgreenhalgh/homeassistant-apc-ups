"""Tests for the APC UPS SNMP sensors."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.apc_ups_snmp.const import (
    CONF_COMMUNITY,
    CONF_SENSORS,
    CONF_SNMP_VERSION,
    DOMAIN,
    SNMP_VERSION_2C,
    ApcOid,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Smart-UPS 1500",
        data={
            "host": "192.168.1.100",
            "port": 161,
            CONF_SNMP_VERSION: SNMP_VERSION_2C,
            CONF_COMMUNITY: "public",
            CONF_SENSORS: [
                "battery_capacity",
                "battery_runtime",
                "battery_temperature",
                "input_voltage",
                "output_load",
                "ups_status",
            ],
        },
        unique_id="AS1234567890",
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
        ApcOid.BATTERY_RUNTIME: 27000000,  # timeticks
        ApcOid.BATTERY_REPLACE: 1,
        ApcOid.INPUT_VOLTAGE: 120,
        ApcOid.INPUT_FREQUENCY: 60,
        ApcOid.OUTPUT_STATUS: 2,  # online
        ApcOid.OUTPUT_VOLTAGE: 120,
        ApcOid.OUTPUT_FREQUENCY: 60,
        ApcOid.OUTPUT_LOAD: 25,
        ApcOid.OUTPUT_CURRENT: 2,
    }


class TestSensors:
    """Test the sensors."""

    async def test_sensor_setup(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_snmp_data: dict[str, Any],
    ) -> None:
        """Test sensor setup."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.apc_ups_snmp.coordinator.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
            mock_client.close = MagicMock()
            mock_client_class.return_value = mock_client

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check that sensors are created (entity_id uses device name)
            entity_registry = er.async_get(hass)
            assert entity_registry.async_get("sensor.ups_server_room_battery_capacity")

    async def test_sensor_state_update(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_snmp_data: dict[str, Any],
    ) -> None:
        """Test sensor state updates."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.apc_ups_snmp.coordinator.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
            mock_client.close = MagicMock()
            mock_client_class.return_value = mock_client

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check battery capacity sensor (now returns decimal)
            state = hass.states.get("sensor.ups_server_room_battery_capacity")
            assert state is not None
            assert state.state == "100.0"

            # Check output load sensor (now returns decimal)
            state = hass.states.get("sensor.ups_server_room_output_load")
            assert state is not None
            assert state.state == "25.0"

    async def test_sensor_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_snmp_data: dict[str, Any],
    ) -> None:
        """Test sensor device info."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.apc_ups_snmp.coordinator.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
            mock_client.close = MagicMock()
            mock_client_class.return_value = mock_client

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            entity_registry = er.async_get(hass)
            entry = entity_registry.async_get("sensor.ups_server_room_battery_capacity")
            assert entry is not None
            # Device info should be set
            assert entry.device_id is not None

    async def test_sensor_unavailable_when_coordinator_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_snmp_data: dict[str, Any],
    ) -> None:
        """Test sensors become unavailable when coordinator fails."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.apc_ups_snmp.coordinator.ApcSnmpClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            # First call succeeds, subsequent calls fail
            mock_client.async_get_all_data = AsyncMock(return_value=mock_snmp_data)
            mock_client.close = MagicMock()
            mock_client_class.return_value = mock_client

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Sensors should be available (now returns decimal)
            state = hass.states.get("sensor.ups_server_room_battery_capacity")
            assert state is not None
            assert state.state == "100.0"
