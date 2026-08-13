"""Config flow for Transport NSW Trip Planner."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateTimeSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TimeSelector,
    TextSelector,
)

from .const import (
    CONF_ARRIVE_BY,
    CONF_DESTINATION,
    CONF_DATE_TIME,
    CONF_JOURNEYS,
    CONF_JOURNEY_TYPE,
    CONF_MAX_RESULTS,
    CONF_MODES,
    CONF_NAME,
    CONF_ORIGIN,
    CONF_TIME,
    CONF_UPDATE_INTERVAL,
    CONF_WEEKDAYS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    JOURNEY_TYPE_FIXED_RECURRING,
    JOURNEY_TYPE_ONE_OFF,
    MODE_MAP,
    WEEKDAY_OPTIONS,
)

ACTION_ADD_JOURNEY = "add_journey"
ACTION_ADD_FIXED_RECURRING = "add_fixed_recurring"
ACTION_ADD_ONE_OFF = "add_one_off"
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
            self._options[CONF_UPDATE_INTERVAL] = int(user_input[CONF_UPDATE_INTERVAL])
            self._options[CONF_JOURNEYS] = self._journeys
            return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self._options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_SECONDS),
                ): NumberSelector(
                    NumberSelectorConfig(min=30, max=86400, mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_add_journey(self, user_input: dict | None = None) -> FlowResult:
        """Choose the type of journey to add."""
        return self.async_show_menu(
            step_id="add_journey",
            menu_options=[ACTION_ADD_FIXED_RECURRING, ACTION_ADD_ONE_OFF],
        )

    async def async_step_add_fixed_recurring(self, user_input: dict | None = None) -> FlowResult:
        """Add a fixed-time recurring journey."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if any(journey[CONF_NAME] == user_input[CONF_NAME] for journey in self._journeys):
                errors[CONF_NAME] = "name_exists"
            else:
                self._journeys.append(
                    {
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_JOURNEY_TYPE: JOURNEY_TYPE_FIXED_RECURRING,
                        CONF_ORIGIN: user_input[CONF_ORIGIN],
                        CONF_DESTINATION: user_input[CONF_DESTINATION],
                        CONF_ARRIVE_BY: user_input[CONF_ARRIVE_BY],
                        CONF_TIME: str(user_input[CONF_TIME]),
                        CONF_WEEKDAYS: user_input[CONF_WEEKDAYS],
                        CONF_MODES: user_input.get(CONF_MODES, []),
                        CONF_MAX_RESULTS: int(user_input[CONF_MAX_RESULTS]),
                    }
                )
                self._options[CONF_JOURNEYS] = self._journeys
                return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Required(CONF_ORIGIN): TextSelector(),
                vol.Required(CONF_DESTINATION): TextSelector(),
                vol.Required(CONF_ARRIVE_BY, default=False): BooleanSelector(),
                vol.Required(CONF_TIME): TimeSelector(),
                vol.Required(
                    CONF_WEEKDAYS,
                    default=["mon", "tue", "wed", "thu", "fri"],
                ): SelectSelector(
                    SelectSelectorConfig(options=list(WEEKDAY_OPTIONS), multiple=True)
                ),
                vol.Optional(CONF_MODES, default=[]): SelectSelector(
                    SelectSelectorConfig(options=list(MODE_OPTIONS), multiple=True)
                ),
                vol.Required(CONF_MAX_RESULTS, default=DEFAULT_MAX_RESULTS): NumberSelector(
                    NumberSelectorConfig(min=1, max=10, mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(
            step_id="add_fixed_recurring", data_schema=schema, errors=errors
        )

    async def async_step_add_one_off(self, user_input: dict | None = None) -> FlowResult:
        """Add a one-off saved journey."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if any(journey[CONF_NAME] == user_input[CONF_NAME] for journey in self._journeys):
                errors[CONF_NAME] = "name_exists"
            else:
                self._journeys.append(
                    {
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_JOURNEY_TYPE: JOURNEY_TYPE_ONE_OFF,
                        CONF_ORIGIN: user_input[CONF_ORIGIN],
                        CONF_DESTINATION: user_input[CONF_DESTINATION],
                        CONF_ARRIVE_BY: user_input[CONF_ARRIVE_BY],
                        CONF_DATE_TIME: _serialize_datetime(user_input[CONF_DATE_TIME]),
                        CONF_MODES: user_input.get(CONF_MODES, []),
                        CONF_MAX_RESULTS: int(user_input[CONF_MAX_RESULTS]),
                    }
                )
                self._options[CONF_JOURNEYS] = self._journeys
                return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Required(CONF_ORIGIN): TextSelector(),
                vol.Required(CONF_DESTINATION): TextSelector(),
                vol.Required(CONF_ARRIVE_BY, default=False): BooleanSelector(),
                vol.Required(CONF_DATE_TIME): DateTimeSelector(),
                vol.Optional(CONF_MODES, default=[]): SelectSelector(
                    SelectSelectorConfig(options=list(MODE_OPTIONS), multiple=True)
                ),
                vol.Required(CONF_MAX_RESULTS, default=DEFAULT_MAX_RESULTS): NumberSelector(
                    NumberSelectorConfig(min=1, max=10, mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="add_one_off", data_schema=schema, errors=errors)

    async def async_step_remove_journey(self, user_input: dict | None = None) -> FlowResult:
        """Remove a saved journey."""
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


def _serialize_datetime(value) -> str:
    """Serialize a datetime selector value."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
