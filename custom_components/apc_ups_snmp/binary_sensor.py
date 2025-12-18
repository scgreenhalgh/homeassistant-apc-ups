"""Binary sensor platform for APC UPS SNMP integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BATTERY_REPLACE_YES,
    BATTERY_STATUS_LOW,
    DOMAIN,
    OUTPUT_STATUS_ON_BATTERY,
    ApcOid,
)
from .coordinator import ApcUpsCoordinator
from .entity import ApcUpsEntity


@dataclass(frozen=True)
class ApcUpsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an APC UPS binary sensor entity."""

    oid: str | None = None
    is_on_fn: Any | None = None


def is_on_battery(data: dict[str, Any]) -> bool | None:
    """Check if UPS is running on battery."""
    status = data.get(ApcOid.OUTPUT_STATUS)
    if status is None:
        return None
    return status == OUTPUT_STATUS_ON_BATTERY


def needs_battery_replacement(data: dict[str, Any]) -> bool | None:
    """Check if battery needs replacement."""
    replace = data.get(ApcOid.BATTERY_REPLACE)
    if replace is None:
        return None
    return replace == BATTERY_REPLACE_YES


def is_low_battery(data: dict[str, Any]) -> bool | None:
    """Check if battery is low."""
    status = data.get(ApcOid.BATTERY_STATUS)
    if status is None:
        return None
    return status == BATTERY_STATUS_LOW


BINARY_SENSOR_DESCRIPTIONS: list[ApcUpsBinarySensorEntityDescription] = [
    ApcUpsBinarySensorEntityDescription(
        key="on_battery",
        translation_key="on_battery",
        name="On Battery",
        device_class=BinarySensorDeviceClass.POWER,
        is_on_fn=is_on_battery,
    ),
    ApcUpsBinarySensorEntityDescription(
        key="replace_battery",
        translation_key="replace_battery",
        name="Replace Battery",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=needs_battery_replacement,
    ),
    ApcUpsBinarySensorEntityDescription(
        key="low_battery",
        translation_key="low_battery",
        name="Low Battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        is_on_fn=is_low_battery,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up APC UPS SNMP binary sensors."""
    coordinator: ApcUpsCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ApcUpsBinarySensor(
            coordinator=coordinator,
            entry_id=entry.entry_id,
            description=description,
        )
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class ApcUpsBinarySensor(ApcUpsEntity, BinarySensorEntity):
    """Representation of an APC UPS binary sensor."""

    entity_description: ApcUpsBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ApcUpsCoordinator,
        entry_id: str,
        description: ApcUpsBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor.

        Args:
            coordinator: The data coordinator.
            entry_id: The config entry ID.
            description: The entity description.
        """
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None

        if self.entity_description.is_on_fn is not None:
            return self.entity_description.is_on_fn(self.coordinator.data)

        return None
