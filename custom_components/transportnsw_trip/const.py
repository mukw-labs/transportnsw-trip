"""Constants for the Transport NSW Trip Planner integration."""

from datetime import timedelta

DOMAIN = "transportnsw_trip"

CONF_API_KEY = "api_key"
CONF_JOURNEYS = "journeys"
CONF_ORIGIN = "origin"
CONF_DESTINATION = "destination"
CONF_NAME = "name"
CONF_MODES = "modes"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ARRIVE_BY = "arrive_by"
CONF_MAX_RESULTS = "max_results"
CONF_JOURNEY_TYPE = "journey_type"
CONF_TIME = "time"
CONF_DATE_TIME = "date_time"
CONF_WEEKDAYS = "weekdays"

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_UPDATE_INTERVAL_SECONDS = 300
DEFAULT_MAX_RESULTS = 5

JOURNEY_TYPE_FIXED_RECURRING = "fixed_recurring"
JOURNEY_TYPE_ONE_OFF = "one_off"

WEEKDAY_OPTIONS = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}

WEEKDAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

SERVICE_PLAN_TRIP = "plan_trip"

ATTR_BEST_OPTION = "best_option"
ATTR_NEXT_OPTION = "next_option"
ATTR_OPTIONS = "options"
ATTR_LAST_UPDATED = "last_updated"

MODE_MAP = {
    "train": 1,
    "metro": 2,
    "light_rail": 4,
    "bus": 5,
    "coach": 7,
    "ferry": 9,
    "school_bus": 11,
}
