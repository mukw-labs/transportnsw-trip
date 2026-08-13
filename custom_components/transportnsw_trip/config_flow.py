"""Config flow for Transport NSW Trip Planner."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ARRIVE_BY,
    CONF_DESTINATION,
    CONF_JOURNEYS,
    CONF_MAX_RESULTS,
    CONF_MODES,
    CONF_NAME,
    CONF_OFFSET_MINUTES,
    CONF_ORIGIN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MAX_RESULTS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    MODE_MAP,
)

ACTION_ADD_JOURNEY = "add_journey"
ACTION_REMOVE_JOURNEY = "remove_journey"
ACTION_SETTINGS = "settings"
FIELD_JOURNEY_TO_REMOVE = "journey_to_remove"

MODE_OPTIONS = {mode: mode.replace("_", " ").title() for mode in MODE_MAP}


class TransportNSWTripConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Transport NSW Trip Planner."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return TransportNSWTripOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id("transportnsw_trip")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Transport NSW Trip Planner", data=user_input)

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class TransportNSWTripOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Transport NSW Trip Planner."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._options = dict(config_entry.options)
        self._journeys = list(self._options.get(CONF_JOURNEYS, []))

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Show the options menu."""
        menu_options = [ACTION_SETTINGS, ACTION_ADD_JOURNEY]
        if self._journeys:
            menu_options.append(ACTION_REMOVE_JOURNEY)

        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
        )

    async def async_step_settings(self, user_input: dict | None = None) -> FlowResult:
        """Configure global polling settings."""
        if user_input is not None:
            self._options[CONF_UPDATE_INTERVAL] = user_input[CONF_UPDATE_INTERVAL]
            self._options[CONF_JOURNEYS] = self._journeys
            return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self._options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=86400)),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_add_journey(self, user_input: dict | None = None) -> FlowResult:
        """Add a configured recurring journey."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if any(journey[CONF_NAME] == user_input[CONF_NAME] for journey in self._journeys):
                errors[CONF_NAME] = "name_exists"
            else:
                self._journeys.append(
                    {
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_ORIGIN: user_input[CONF_ORIGIN],
                        CONF_DESTINATION: user_input[CONF_DESTINATION],
                        CONF_ARRIVE_BY: user_input[CONF_ARRIVE_BY],
                        CONF_OFFSET_MINUTES: user_input[CONF_OFFSET_MINUTES],
                        CONF_MODES: user_input.get(CONF_MODES, []),
                        CONF_MAX_RESULTS: user_input[CONF_MAX_RESULTS],
                    }
                )
                self._options[CONF_JOURNEYS] = self._journeys
                return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_ORIGIN): str,
                vol.Required(CONF_DESTINATION): str,
                vol.Required(CONF_ARRIVE_BY, default=False): bool,
                vol.Required(CONF_OFFSET_MINUTES, default=0): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=1440)
                ),
                vol.Optional(CONF_MODES, default=[]): cv.multi_select(MODE_OPTIONS),
                vol.Required(CONF_MAX_RESULTS, default=DEFAULT_MAX_RESULTS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=10)
                ),
            }
        )
        return self.async_show_form(step_id="add_journey", data_schema=schema, errors=errors)

    async def async_step_remove_journey(self, user_input: dict | None = None) -> FlowResult:
        """Remove a configured recurring journey."""
        if not self._journeys:
            return self.async_create_entry(title="", data=self._options)

        if user_input is not None:
            selected = user_input[FIELD_JOURNEY_TO_REMOVE]
            self._journeys = [
                journey for journey in self._journeys if journey[CONF_NAME] != selected
            ]
            self._options[CONF_JOURNEYS] = self._journeys
            return self.async_create_entry(title="", data=self._options)

        choices = {journey[CONF_NAME]: journey[CONF_NAME] for journey in self._journeys}
        schema = vol.Schema({vol.Required(FIELD_JOURNEY_TO_REMOVE): vol.In(choices)})
        return self.async_show_form(step_id="remove_journey", data_schema=schema)
