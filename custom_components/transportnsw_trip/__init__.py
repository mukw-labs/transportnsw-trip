"""Transport NSW Trip Planner integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_API_KEY, CONF_JOURNEYS, DOMAIN
from .coordinator import TransportNSWTripCoordinator
from .entity_helpers import desired_device_identifiers, desired_unique_ids
from .services import async_setup_services, async_unload_services
from .tfnsw_client import TransportNSWClient

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Transport NSW Trip Planner from a config entry."""
    LOGGER.debug("Setting up Transport NSW Trip Planner entry %s", entry.entry_id)
    api_key = entry.data[CONF_API_KEY]
    client = TransportNSWClient(async_get_clientsession(hass), api_key)
    coordinator = TransportNSWTripCoordinator(hass, entry, client)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    async_setup_services(hass)
    _async_remove_stale_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_refresh()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading Transport NSW Trip Planner entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            async_unload_services(hass)
            hass.data.pop(DOMAIN)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    LOGGER.debug("Reloading Transport NSW Trip Planner entry %s after options update", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


def _async_remove_stale_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove registry entries for journeys no longer configured."""
    registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    journeys = entry.options.get(CONF_JOURNEYS, [])
    expected_unique_ids = desired_unique_ids(entry.entry_id, journeys)
    expected_device_identifiers = desired_device_identifiers(entry.entry_id, journeys)

    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity_entry.platform != DOMAIN:
            continue
        if entity_entry.unique_id in expected_unique_ids:
            continue
        LOGGER.info("Removing stale Transport NSW Trip Planner entity %s", entity_entry.entity_id)
        registry.async_remove(entity_entry.entity_id)

    for device_entry in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        transportnsw_identifiers = {
            identifier
            for identifier in device_entry.identifiers
            if identifier[0] == DOMAIN and identifier[1].startswith(f"{entry.entry_id}_")
        }
        if not transportnsw_identifiers:
            continue
        if transportnsw_identifiers & expected_device_identifiers:
            continue
        LOGGER.info("Removing stale Transport NSW Trip Planner device %s", device_entry.name)
        device_registry.async_remove_device(device_entry.id)
