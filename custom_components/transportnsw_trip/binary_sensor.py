"""Binary sensors for Transport NSW Trip Planner."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_JOURNEYS, CONF_NAME, DOMAIN
from .coordinator import TransportNSWTripCoordinator
from .entity_helpers import journey_device_info, journey_unique_id


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up binary sensors for configured journeys."""
    coordinator: TransportNSWTripCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = [
        TripDisruptedBinarySensor(
            coordinator,
            entry.entry_id,
            journey[CONF_NAME],
            journey_device_info(entry, journey),
        )
        for journey in entry.options.get(CONF_JOURNEYS, [])
    ]
    async_add_entities(entities)


class TripDisruptedBinarySensor(
    CoordinatorEntity[TransportNSWTripCoordinator], BinarySensorEntity
):
    """Indicates whether the best trip option is meaningfully late."""

    _attr_has_entity_name = True
    _attr_translation_key = "disrupted"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: TransportNSWTripCoordinator,
        entry_id: str,
        journey_name: str,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._journey_name = journey_name
        self._attr_unique_id = journey_unique_id(entry_id, journey_name, "disrupted")
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        """Return true when lateness is five minutes or more."""
        if not self.coordinator.data:
            return None
        trip = self.coordinator.data.get(self._journey_name, {})
        best = trip.get("best_option")
        if not best:
            return None
        return best.get("lateness_minutes", 0) >= 5
