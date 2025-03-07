"""Constants for DiveraControl Integration."""

# general
DOMAIN = "diveracontrol"
VERSION = "0"
MINOR_VERSION = "8"
PATCH_VERSION = "1"
MANUFACTURER = "Divera GmbH"
# UPDATE_INTERVAL_OPS = 45
UPDATE_INTERVAL_DATA = 60
UPDATE_INTERVAL_ALARM = 30
# UPDATE_INTERVAL_MASTERDATA = 86400

# api
BASE_API_URL = "https://app.divera247.com/"
BASE_API_V2_URL = "api/v2/"
API_ACCESS_KEY = "accesskey"
API_AUTH_LOGIN = "auth/login"
API_UCR = "ucr="
API_AUTH = "auth"
API_PULL_ALL = "pull/all"
API_PULL_VEHICLE = "pull/vehicle-status"
API_ALARM = "alarms"
API_NEWS = "news"
API_EVENT = "event"
API_MESSAGE_CHANNEL = "message-channel"
API_MESSAGES = "messages"
API_STATUSGEBER = "statusgeber/set-status"
API_STATUSGEBER_SIMPLE = "statusgeber.html"
API_USING_VEHICLE_SET_SINGLE = "using-vehicles/set-status"
API_USING_VEHICLE_PROP = "using-vehicle-property"
API_USING_VEHICLE_CREW = "using-vehicle-crew"
API_OPERATIONS = "operations"

# data
# D_UPDATE_INTERVAL_OPS = "update_interval_alarms"
D_UPDATE_INTERVAL_DATA = "update_interval_data"
D_UPDATE_INTERVAL_ALARM = "update_interval_alarm"
D_LAST_UPDATE_ALARM = "last_update_alarm"
D_LAST_UPDATE_DATA = "last_update_data"
D_DATA = "data"
D_API_KEY = "api_key"
D_HUB_ID = "hub_id"
D_UCR = "ucr"
D_UCR_ID = "ucr_id"
D_CLUSTER_ID = "cluster_id"
D_CLUSTER_NAME = "cluster_name"
D_COORDINATOR = "coordinator"
# D_CLUSTER_ID = "cluster_id"
# D_ALARMS = "alarms"
# D_VEHICLE_STATUS = "vehicle_status"
D_ACTIVE_ALARM_COUNT = "active_alarm_count"
D_STATUS_CONF = "status_conf"
# D_STATUS_ID = "status_ids"
D_STATUS_SORT = "status_sorting"
# D_STATUS_DATA = "status_data"
# start new structure
D_UCR = "ucr"
D_UCR_DEFAULT = "ucr_default"
D_UCR_ACTIVE = "ucr_active"
D_USERNAME = "user_name"
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
D_CLUSTER_ADDRESS = "cluster_address"
D_VEHICLE = "vehicle"


# permissions
# PERM_MANAGER = "management"
# PERM_ALARM = "alarm"
# PERM_STATUS = "status"
# PERM_NEWS = "news"
# PERM_EVENT = "event"
# PERM_MESSAGE_CHANNEL = "message_channel"
# PERM_MONITOR = "monitor"
# new_permissions
PERM_MESSAGES = "messages"
PERM_ALARM = "alarm"
PERM_NEWS = "news"
PERM_EVENT = "event"
PERM_MESSAGE_CHANNEL = "message_channel"
PERM_REPORT = "report"
PERM_STATUS = "status"
PERM_STATUS_MANUAL = "status_manual"
PERM_STATUS_PLANER = "status_planer"
PERM_STATUS_GEOFENCE = "status_geofence"
PERM_STATUS_VEHICLE = "status_vehicle"
PERM_MONITOR = "monitor"
PERM_MONITOR_SHOW_NAMES = "monitor_show_names"
PERM_PERSONNEL_PHONENUMBERS = "personnel_phonenumbers"
PERM_LOCALMANAGEMENT = "localmanagement"
PERM_MANAGEMENT = "management"
PERM_DASHBOARD = "dashboard"
PERM_CROSS_UNIT = "cross_unit"
PERM_LOCALMONITOR = "localmonitor"
PERM_LOCALMONITOR_SHOW_NAMES = "localmonitor_show_names"
PERM_FMS_EDITOR = "fms_editor"


# icons
I_OPEN_ALARM = "mdi:alarm-light-outline"
I_OPEN_ALARM_NOPRIO = "mdi:alarm-light-off-outline"
I_CLOSED_ALARM = "mdi:check-circle-outline"
I_VEHICLE = "mdi:fire-truck"
I_FIRESTATION = "mdi:fire-station"
I_COUNTER_ACTIVE_ALARMS = "mdi:counter"
I_STATUS = "mdi:run-fast"
I_MAPMARKER_ALERT = "mdi:map-marker-alert-outline"
I_MAPMARKER_CHECK = "mdi:map-marker-check-outline"
I_MAPMARKER_VEHICLE = "mdi:car-emergency"
