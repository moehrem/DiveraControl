"""Constants for DiveraControl Integration."""

import json
from pathlib import Path

# Load version from manifest.json
_MANIFEST_PATH = Path(__file__).parent / "manifest.json"
with _MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
    _MANIFEST = json.load(manifest_file)

_VERSION_PARTS = _MANIFEST["version"].split(".")
VERSION = int(_VERSION_PARTS[0])
MINOR_VERSION = int(_VERSION_PARTS[1])
PATCH_VERSION = int(_VERSION_PARTS[2])

# general
DOMAIN = "diveracontrol"
MANUFACTURER = "Divera GmbH"
UPDATE_INTERVAL_DATA = 60
UPDATE_INTERVAL_ALARM = 30
DEFAULT_COORDINATOR = "coordinator"
DEFAULT_API = "api"
DEFAULT_SENSORS = "sensors"
DEFAULT_DEVICE_TRACKER = "device_tracker"
LOG_FILE = "home-assistant.log"

# api
BASE_API_URL = "https://app.divera247.com/"
BASE_API_V2_URL = "api/v2/"
API_ACCESS_KEY = "accesskey"
API_AUTH_LOGIN = "auth/login"
API_PULL_ALL = "pull/all"
API_ALARM = "alarms"
API_EVENT = "event"
API_MESSAGES = "messages"
API_NEWS = "news"
API_USING_VEHICLE_SET_SINGLE = "using-vehicles/set-status"
API_USING_VEHICLE_PROP = "using-vehicle-property"
API_USING_VEHICLE_CREW = "using-vehicle-crew"

# data
D_UPDATE_INTERVAL_DATA = "update_interval_data"
D_UPDATE_INTERVAL_ALARM = "update_interval_alarm"
D_DATA = "data"
D_NAME = "name"
D_API_KEY = "api_key"
D_ENTRY_ID = "config_entry_id"
D_USERGROUP_ID = "usergroup_id"
D_UCR = "ucr"
D_UCR_ID = "ucr_id"
D_CLUSTER_NAME = "cluster_name"
D_COORDINATOR = "coordinator"
D_OPEN_ALARMS = "open_alarms"
D_UCR_DEFAULT = "ucr_default"
D_UCR_ACTIVE = "ucr_active"
D_TS = "ts"
D_USER = "user"
D_STATUS = "status"
D_CLUSTER = "cluster"
D_MONITOR = "monitor"
D_ALARM = "alarm"
D_NEWS = "news"
D_EVENTS = "events"
D_DM = "dm"
D_MESSAGE_CHANNEL = "message_channel"
D_MESSAGE = "message"
D_LOCALMONITOR = "localmonitor"
D_STATUSPLAN = "statusplan"
D_ACCESS = "access"
D_VEHICLE = "vehicle"
D_FMS_STATUS = "fms_status"

# permissions
PERM_MESSAGES = "messages"
PERM_ALARM = "alarm"
PERM_STATUS_VEHICLE = "status_vehicle"
PERM_MANAGEMENT = "management"
PERM_NEWS = "news"

# icons
I_OPEN_ALARM = "mdi:alarm-light-outline"
I_OPEN_ALARM_NOPRIO = "mdi:alarm-light-off-outline"
I_CLOSED_ALARM = "mdi:check-circle-outline"
I_VEHICLE = "mdi:fire-truck"
I_FIRESTATION = "mdi:fire-station"
I_COUNTER_ACTIVE_ALARMS = "mdi:counter"
I_AVAILABILITY = "mdi:run-fast"
