"""Config flow for APC UPS SNMP integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    AUTH_PROTOCOLS,
    CONF_AUTH_PASSWORD,
    CONF_AUTH_PROTOCOL,
    CONF_COMMUNITY,
    CONF_PRIV_PASSWORD,
    CONF_PRIV_PROTOCOL,
    CONF_SENSORS,
    CONF_SNMP_VERSION,
    DEFAULT_PORT,
    DOMAIN,
    PRIV_PROTOCOLS,
    SNMP_VERSION_2C,
    SNMP_VERSION_3,
)
from .snmp_client import (
    ApcSnmpClient,
    SnmpAuthError,
    SnmpConnectionError,
    SnmpTimeoutError,
)

_LOGGER = logging.getLogger(__name__)

# Available sensors for selection
AVAILABLE_SENSORS = {
    "battery_capacity": "Battery Capacity",
    "battery_runtime": "Battery Runtime",
    "battery_temperature": "Battery Temperature",
    "battery_voltage": "Battery Voltage",
    "input_voltage": "Input Voltage",
    "input_frequency": "Input Frequency",
    "output_voltage": "Output Voltage",
    "output_frequency": "Output Frequency",
    "output_load": "Output Load",
    "output_current": "Output Current",
    "ups_status": "UPS Status",
}

# Default sensors to enable
DEFAULT_SENSORS = [
    "battery_capacity",
    "battery_runtime",
    "output_load",
    "ups_status",
]


class ApcUpsSnmpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for APC UPS SNMP."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._ups_identity: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            if user_input[CONF_SNMP_VERSION] == SNMP_VERSION_2C:
                return await self.async_step_auth_v2c()
            else:
                return await self.async_step_auth_v3()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_SNMP_VERSION, default=SNMP_VERSION_2C): vol.In(
                        [SNMP_VERSION_2C, SNMP_VERSION_3]
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_auth_v2c(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle SNMP v2c authentication step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            # Test connection
            error = await self._test_connection()
            if error:
                errors["base"] = error
            else:
                # Check for duplicate
                await self.async_set_unique_id(self._ups_identity.get("serial"))
                self._abort_if_unique_id_configured()

                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="auth_v2c",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COMMUNITY, default="public"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_auth_v3(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle SNMP v3 authentication step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            # Test connection
            error = await self._test_connection()
            if error:
                errors["base"] = error
            else:
                # Check for duplicate
                await self.async_set_unique_id(self._ups_identity.get("serial"))
                self._abort_if_unique_id_configured()

                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="auth_v3",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Optional(CONF_AUTH_PROTOCOL): vol.In(AUTH_PROTOCOLS),
                    vol.Optional(CONF_AUTH_PASSWORD): str,
                    vol.Optional(CONF_PRIV_PROTOCOL): vol.In(PRIV_PROTOCOLS),
                    vol.Optional(CONF_PRIV_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle sensor selection step."""
        if user_input is not None:
            self._data[CONF_SENSORS] = user_input.get(CONF_SENSORS, DEFAULT_SENSORS)

            return self.async_create_entry(
                title=self._ups_identity.get("model", "APC UPS"),
                data=self._data,
            )

        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SENSORS, default=DEFAULT_SENSORS
                    ): vol.All(
                        vol.Coerce(list),
                        [vol.In(list(AVAILABLE_SENSORS.keys()))],
                    ),
                }
            ),
            description_placeholders={
                "model": self._ups_identity.get("model", "Unknown"),
                "serial": self._ups_identity.get("serial", "Unknown"),
            },
        )

    async def _test_connection(self) -> str | None:
        """Test the SNMP connection and get UPS identity.

        Returns:
            Error string if connection failed, None if successful.
        """
        client = self._create_client()

        try:
            await client.async_test_connection()
            self._ups_identity = await client.async_get_identity()
            return None
        except SnmpTimeoutError:
            return "timeout"
        except SnmpAuthError:
            return "invalid_auth"
        except SnmpConnectionError:
            return "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error during connection test")
            return "unknown"
        finally:
            client.close()

    def _create_client(self) -> ApcSnmpClient:
        """Create an SNMP client from the current data."""
        if self._data.get(CONF_SNMP_VERSION) == SNMP_VERSION_2C:
            return ApcSnmpClient(
                host=self._data[CONF_HOST],
                port=self._data[CONF_PORT],
                version=SNMP_VERSION_2C,
                community=self._data.get(CONF_COMMUNITY),
            )
        else:
            return ApcSnmpClient(
                host=self._data[CONF_HOST],
                port=self._data[CONF_PORT],
                version=SNMP_VERSION_3,
                username=self._data.get(CONF_USERNAME),
                auth_protocol=self._data.get(CONF_AUTH_PROTOCOL),
                auth_password=self._data.get(CONF_AUTH_PASSWORD),
                priv_protocol=self._data.get(CONF_PRIV_PROTOCOL),
                priv_password=self._data.get(CONF_PRIV_PASSWORD),
            )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return ApcUpsSnmpOptionsFlow(config_entry)


class ApcUpsSnmpOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for APC UPS SNMP."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_sensors = self.config_entry.options.get(
            CONF_SENSORS, self.config_entry.data.get(CONF_SENSORS, DEFAULT_SENSORS)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SENSORS, default=current_sensors
                    ): vol.All(
                        vol.Coerce(list),
                        [vol.In(list(AVAILABLE_SENSORS.keys()))],
                    ),
                }
            ),
        )
