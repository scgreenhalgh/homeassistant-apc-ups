"""Base entity for APC UPS SNMP integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ApcOid, DOMAIN
from .coordinator import ApcUpsCoordinator


class ApcUpsEntity(CoordinatorEntity[ApcUpsCoordinator]):
    """Base entity for APC UPS devices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ApcUpsCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data coordinator.
            entry_id: The config entry ID.
        """
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=data.get(ApcOid.NAME, "APC UPS"),
            manufacturer="APC by Schneider Electric",
            model=data.get(ApcOid.MODEL, "Unknown"),
            sw_version=data.get(ApcOid.FIRMWARE),
            serial_number=data.get(ApcOid.SERIAL),
        )
