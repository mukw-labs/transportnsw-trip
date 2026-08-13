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
CONF_OFFSET_MINUTES = "offset_minutes"
CONF_ARRIVE_BY = "arrive_by"
CONF_MAX_RESULTS = "max_results"

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)
DEFAULT_UPDATE_INTERVAL_SECONDS = 300
DEFAULT_MAX_RESULTS = 5

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
