"""Sensors for Transport NSW Trip Planner."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_JOURNEYS, CONF_NAME, DOMAIN
from .coordinator import TransportNSWTripCoordinator
from .entity_helpers import (
    journey_device_info,
    journey_suggested_object_id,
    journey_unique_id,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors for configured journeys."""
    coordinator: TransportNSWTripCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = []

    for journey in entry.options.get(CONF_JOURNEYS, []):
        name = journey[CONF_NAME]
        device_info = journey_device_info(entry, journey)
        entities.append(TripDelaySensor(coordinator, entry.entry_id, name, device_info))
        entities.append(TripBestDepartureSensor(coordinator, entry.entry_id, name, device_info))
        entities.append(TripNextDelaySensor(coordinator, entry.entry_id, name, device_info))
        entities.append(TripNextDepartureSensor(coordinator, entry.entry_id, name, device_info))

    async_add_entities(entities)


class TripSensorBase(CoordinatorEntity[TransportNSWTripCoordinator], SensorEntity):
    """Base sensor for configured journeys."""

    _attr_has_entity_name = True

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
        self._attr_unique_id = journey_unique_id(entry_id, journey_name, self.sensor_key)
        self._attr_translation_key = self.sensor_key
        self._attr_suggested_object_id = journey_suggested_object_id(
            journey_name, self.sensor_key
        )
        self._attr_device_info = device_info

    @property
    def data(self) -> dict[str, Any] | None:
        """Return the journey data."""
        return self.coordinator.data.get(self._journey_name) if self.coordinator.data else None


class TripDelaySensor(TripSensorBase):
    """Recommended option arrival delay sensor."""

    sensor_key = "best_delay"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> int | None:
        """Return best option lateness in minutes."""
        best = (self.data or {}).get("best_option")
        return None if not best else best.get("lateness_minutes")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return best and next option details."""
        data = self.data
        if not data:
            return None
        return {
            "best_option": data.get("best_option"),
            "next_option": data.get("next_option"),
            "last_updated": data.get("last_updated"),
        }


class TripBestDepartureSensor(TripSensorBase):
    """Recommended option predicted departure sensor."""

    sensor_key = "best_departure"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return best option departure timestamp."""
        best = (self.data or {}).get("best_option")
        if not best:
            return None
        return datetime.fromisoformat(best["departure_time"])


class TripNextDelaySensor(TripSensorBase):
    """Next option arrival delay sensor."""

    sensor_key = "next_delay"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> int | None:
        """Return next option lateness in minutes."""
        next_option = (self.data or {}).get("next_option")
        return None if not next_option else next_option.get("lateness_minutes")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return next option details."""
        data = self.data
        if not data:
            return None
        return {
            "next_option": data.get("next_option"),
            "last_updated": data.get("last_updated"),
        }


class TripNextDepartureSensor(TripSensorBase):
    """Next option predicted departure sensor."""

    sensor_key = "next_departure"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return next option departure timestamp."""
        next_option = (self.data or {}).get("next_option")
        if not next_option:
            return None
        return datetime.fromisoformat(next_option["departure_time"])
