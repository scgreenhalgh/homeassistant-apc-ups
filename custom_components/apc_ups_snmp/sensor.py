"""Sensor platform for APC UPS SNMP integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SENSORS,
    DOMAIN,
    LAST_TRANSFER_CAUSE_MAP,
    OUTPUT_STATUS_MAP,
    ApcOid,
)
from .coordinator import ApcUpsCoordinator
from .entity import ApcUpsEntity


@dataclass(frozen=True)
class ApcUpsSensorEntityDescription(SensorEntityDescription):
    """Describes an APC UPS sensor entity."""

    oid: str | None = None
    value_fn: Any | None = None


def runtime_timeticks_to_minutes(value: int | None) -> float | None:
    """Convert SNMP timeticks to minutes.

    APC reports runtime in hundredths of a second (timeticks).
    """
    if value is None:
        return None
    # Timeticks are 1/100 of a second
    seconds = value / 100
    return round(seconds / 60, 1)


def timeticks_to_seconds(value: int | None) -> float | None:
    """Convert SNMP timeticks to seconds.

    APC reports time on battery in hundredths of a second (timeticks).
    """
    if value is None:
        return None
    # Timeticks are 1/100 of a second
    return round(value / 100, 1)


def output_status_to_string(value: int | None) -> str | None:
    """Convert output status code to string."""
    if value is None:
        return None
    return OUTPUT_STATUS_MAP.get(value, "unknown")


def last_transfer_cause_to_string(value: int | None) -> str | None:
    """Convert last transfer cause code to string."""
    if value is None:
        return None
    return LAST_TRANSFER_CAUSE_MAP.get(value, "Unknown")


def to_one_decimal(value: int | float | None) -> float | None:
    """Round value to 1 decimal place.

    Always returns a float to ensure decimal display (e.g., 100.0 not 100).
    """
    if value is None:
        return None
    # Ensure we always return a float, not int
    result = round(float(value), 1)
    # Force float type even for whole numbers
    return float(result)


SENSOR_DESCRIPTIONS: dict[str, ApcUpsSensorEntityDescription] = {
    "battery_capacity": ApcUpsSensorEntityDescription(
        key="battery_capacity",
        translation_key="battery_capacity",
        name="Battery Capacity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.BATTERY_CAPACITY,
        value_fn=to_one_decimal,
    ),
    "battery_runtime": ApcUpsSensorEntityDescription(
        key="battery_runtime",
        translation_key="battery_runtime",
        name="Battery Runtime",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.BATTERY_RUNTIME,
        value_fn=runtime_timeticks_to_minutes,
    ),
    "battery_temperature": ApcUpsSensorEntityDescription(
        key="battery_temperature",
        translation_key="battery_temperature",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.BATTERY_TEMPERATURE,
        value_fn=to_one_decimal,
    ),
    "battery_voltage": ApcUpsSensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.BATTERY_VOLTAGE,
        value_fn=to_one_decimal,
    ),
    "time_on_battery": ApcUpsSensorEntityDescription(
        key="time_on_battery",
        translation_key="time_on_battery",
        name="Time On Battery",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.TIME_ON_BATTERY,
        value_fn=timeticks_to_seconds,
    ),
    "input_voltage": ApcUpsSensorEntityDescription(
        key="input_voltage",
        translation_key="input_voltage",
        name="Input Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.INPUT_VOLTAGE,
        value_fn=to_one_decimal,
    ),
    "input_frequency": ApcUpsSensorEntityDescription(
        key="input_frequency",
        translation_key="input_frequency",
        name="Input Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.INPUT_FREQUENCY,
        value_fn=to_one_decimal,
    ),
    "last_transfer_cause": ApcUpsSensorEntityDescription(
        key="last_transfer_cause",
        translation_key="last_transfer_cause",
        name="Last Transfer Cause",
        device_class=SensorDeviceClass.ENUM,
        oid=ApcOid.LAST_TRANSFER_CAUSE,
        value_fn=last_transfer_cause_to_string,
        options=list(LAST_TRANSFER_CAUSE_MAP.values()),
    ),
    "output_voltage": ApcUpsSensorEntityDescription(
        key="output_voltage",
        translation_key="output_voltage",
        name="Output Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.OUTPUT_VOLTAGE,
        value_fn=to_one_decimal,
    ),
    "output_frequency": ApcUpsSensorEntityDescription(
        key="output_frequency",
        translation_key="output_frequency",
        name="Output Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.OUTPUT_FREQUENCY,
        value_fn=to_one_decimal,
    ),
    "output_load": ApcUpsSensorEntityDescription(
        key="output_load",
        translation_key="output_load",
        name="Output Load",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.OUTPUT_LOAD,
        value_fn=to_one_decimal,
    ),
    "output_current": ApcUpsSensorEntityDescription(
        key="output_current",
        translation_key="output_current",
        name="Output Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.OUTPUT_CURRENT,
        value_fn=to_one_decimal,
    ),
    "output_power": ApcUpsSensorEntityDescription(
        key="output_power",
        translation_key="output_power",
        name="Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        oid=ApcOid.OUTPUT_POWER,
        value_fn=to_one_decimal,
    ),
    "ups_status": ApcUpsSensorEntityDescription(
        key="ups_status",
        translation_key="ups_status",
        name="UPS Status",
        device_class=SensorDeviceClass.ENUM,
        oid=ApcOid.OUTPUT_STATUS,
        value_fn=output_status_to_string,
        options=list(OUTPUT_STATUS_MAP.values()),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up APC UPS SNMP sensors."""
    coordinator: ApcUpsCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Get selected sensors from config
    selected_sensors = entry.data.get(CONF_SENSORS, [])
    if not selected_sensors:
        # Default sensors if none selected
        selected_sensors = list(SENSOR_DESCRIPTIONS.keys())

    # Apply options if they override data
    if entry.options.get(CONF_SENSORS):
        selected_sensors = entry.options[CONF_SENSORS]

    entities = []
    for sensor_key in selected_sensors:
        if sensor_key in SENSOR_DESCRIPTIONS:
            entities.append(
                ApcUpsSensor(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    description=SENSOR_DESCRIPTIONS[sensor_key],
                )
            )

    async_add_entities(entities)


class ApcUpsSensor(ApcUpsEntity, SensorEntity):
    """Representation of an APC UPS sensor."""

    entity_description: ApcUpsSensorEntityDescription

    def __init__(
        self,
        coordinator: ApcUpsCoordinator,
        entry_id: str,
        description: ApcUpsSensorEntityDescription,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The data coordinator.
            entry_id: The config entry ID.
            description: The entity description.
        """
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None

        oid = self.entity_description.oid
        if oid is None:
            return None

        value = self.coordinator.data.get(oid)

        # Apply value transformation if defined
        if self.entity_description.value_fn is not None:
            value = self.entity_description.value_fn(value)

        return value
