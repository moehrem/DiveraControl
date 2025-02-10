"""Methoden zur Verarbeitung und Aktualisierung der API-Daten.

Verantwortung:
    - Festlegen, wie oft Daten abgerufen werden.
    - Verwenden von Methoden aus der api.py, um Daten von der API abzurufen.
    - Fehlerbehandlung (z. B. Logging oder UpdateFailed werfen).

Kommunikation:
    - Ruft die API-Methoden aus api.py auf.
    - Rückgabe ermittelter und verarbeiteter Daten an coordinator.py.
    - Dient als zentrale Schnittstelle, über die andere Plattformen (sensor, binary_sensor, etc.) auf die Daten zugreifen.
"""

import logging

from aiohttp import ClientError

from .const import (
    # data
    D_API_KEY,
    D_DATA,
    D_ACTIVE_ALARM_COUNT,
    D_UCR,
    D_UCR_DEFAULT,
    D_UCR_ACTIVE,
    D_TS,
    D_USER,
    D_STATUS,
    D_CLUSTER,
    D_MONITOR,
    D_ALARM,
    D_NEWS,
    D_EVENTS,
    D_DM,
    D_MESSAGE_CHANNEL,
    D_MESSAGE,
    D_LOCALMONITOR,
    D_STATUSPLAN,
    D_ACCESS,
    D_CLUSTER_ADDRESS,
    D_VEHICLE,
    D_UCR_ID,
    D_STATUS_SORT,
    D_STATUS_CONF,
    # permissions
    PERM_MESSAGES,
    PERM_ALARM,
    PERM_NEWS,
    PERM_EVENT,
    PERM_MESSAGE_CHANNEL,
    PERM_REPORT,
    PERM_STATUS,
    PERM_STATUS_MANUAL,
    PERM_STATUS_PLANER,
    PERM_STATUS_GEOFENCE,
    PERM_STATUS_VEHICLE,
    PERM_MONITOR,
    PERM_MONITOR_SHOW_NAMES,
    PERM_PERSONNEL_PHONENUMBERS,
    PERM_LOCALMANAGEMENT,
    PERM_MANAGEMENT,
    PERM_DASHBOARD,
    PERM_CROSS_UNIT,
    PERM_LOCALMONITOR,
    PERM_LOCALMONITOR_SHOW_NAMES,
    PERM_FMS_EDITOR,
)

_LOGGER = logging.getLogger(__name__)


async def update_operational_data(api, data):
    """Update operational data from the Divera API.

    This method fetches all short live data from the Divera API and updates
    the given data dictionary accordingly. The data includes alarm details,
    vehicle positions and statuses, availability status.

    Steps:
    1. Retrieve alarm data and filter by cluster ID.
    2. Update alarm details and count of active alarms.
    3. Fetch and process vehicle status data.

    Args:
        api (DiveraAPI): The API instance used to communicate with Divera.
        data (dict): A dictionary to store and update alarm and vehicle data.

    Exceptions:
        Logs errors for network issues, invalid data, or missing keys in API responses.
        Sets alarm and vehicle data to empty if any issues occur.

    Returns:
        None: Updates the `data` dictionary in place.

    """
    try:
        ucr_id = data[D_UCR_ID]
        api.set_api_key(data.get(D_API_KEY, ""))
        raw_ucr_data = await api.get_ucr_data(ucr_id)

        # check for successful API response data
        if not raw_ucr_data.get("success", False):
            _LOGGER.error(
                "Unexpected data format or API request failed: %s",
                raw_ucr_data,
            )
            return

        # set data
        ucr = raw_ucr_data.get(D_DATA, {}).get(D_UCR, {})
        ucr_default = raw_ucr_data.get(D_DATA, {}).get(D_UCR_DEFAULT, {})
        ucr_active = raw_ucr_data.get(D_DATA, {}).get(D_UCR_ACTIVE, {})
        ts = raw_ucr_data.get(D_DATA, {}).get(D_TS, {})
        user = raw_ucr_data.get(D_DATA, {}).get(D_USER, {})
        status = raw_ucr_data.get(D_DATA, {}).get(D_STATUS, {})
        cluster = raw_ucr_data.get(D_DATA, {}).get(D_CLUSTER, {})
        monitor = raw_ucr_data.get(D_DATA, {}).get(D_MONITOR, {})
        alarm = raw_ucr_data.get(D_DATA, {}).get(D_ALARM, {})
        news = raw_ucr_data.get(D_DATA, {}).get(D_NEWS, {})
        events = raw_ucr_data.get(D_DATA, {}).get(D_EVENTS, {})
        dm = raw_ucr_data.get(D_DATA, {}).get(D_DM, {})
        message_channel = raw_ucr_data.get(D_DATA, {}).get(D_MESSAGE_CHANNEL, {})
        message = raw_ucr_data.get(D_DATA, {}).get(D_MESSAGE, {})
        localmonitor = raw_ucr_data.get(D_DATA, {}).get(D_LOCALMONITOR, {})
        statusplan = raw_ucr_data.get(D_DATA, {}).get(D_STATUSPLAN, {})

        #####################
        ###  MASTER DATA  ###
        #####################

        # updating permission data
        try:
            access = user.get(D_ACCESS, {})

            for key in access:
                data[D_ACCESS][key] = access.get(key, False)

            _LOGGER.debug("Access permissions data updated: %s", data)
        except KeyError as e:
            _LOGGER.error("Error handling access permissions: %s", e)

        # handling status master data
        try:
            status_conf = cluster.get("status", {})
            status_sort = cluster.get("statussorting_statusgeber", {})
            data[D_STATUS_CONF] = status_conf
            data[D_STATUS_SORT] = status_sort

            _LOGGER.debug(
                "Status configuration updated: %s, sorting: %s",
                status_conf,
                status_sort,
            )

        except KeyError as e:
            _LOGGER.error("Error updating status configuration: %s", e)

        # handling cluster address data
        try:
            name = cluster.get("name", "Unknown")
            shortname = cluster.get("shortname", "Unknown")
            address = cluster.get("address", {})

            cluster_address_data = {
                str(name): {
                    "shortname": shortname,
                    "address": address,
                }
            }
            data[D_CLUSTER_ADDRESS] = cluster_address_data
            _LOGGER.debug("Fire station data updated: %s", cluster_address_data)
        except KeyError as e:
            _LOGGER.error("Error updating firestation data: %s", e)
            data[D_CLUSTER_ADDRESS] = {"name": "Unknown"}

        #########################
        ###  OPERATIONAL DATA ###
        #########################

        # handle vehicle data
        try:
            vehicle_data = cluster.get(D_VEHICLE, {})
            data[D_VEHICLE] = vehicle_data.copy()
            _LOGGER.debug("Vehicle data updated: %s", vehicle_data)

            # adding properties to vehicle
            for key in vehicle_data.keys():
                raw_vehicle_property = await api.get_vehicle_property(key)
                vehicle_property = raw_vehicle_property.get(D_DATA, {})
                if isinstance(vehicle_property, dict):
                    data[D_VEHICLE][key].update(vehicle_property)
                else:
                    _LOGGER.warning(
                        "Unexpected vehicle property format for %s: %s",
                        key,
                        vehicle_property,
                    )

        except (ClientError, ValueError, KeyError) as e:
            _LOGGER.error("Error updating vehicles: %s", e)

        # handle status data
        try:
            data[D_STATUS] = status
            _LOGGER.debug("Status data updated: %s", status)

        except (ClientError, ValueError, KeyError) as e:
            _LOGGER.error("Error updating status: %s", e)

        # handle alarm data
        try:
            alarm_data = alarm.get("items", {}) if alarm.get("items") else {}
            data[D_ALARM] = alarm_data

            if not alarm_data:
                active_alarm_count = 0

            else:
                active_alarm_count = sum(
                    1
                    for alarm_details in alarm_data.values()
                    if not alarm_details.get("closed", True)
                )
                if not active_alarm_count:
                    active_alarm_count = 0

            data[D_ACTIVE_ALARM_COUNT] = active_alarm_count
            _LOGGER.debug("Alarm count updated: %s", active_alarm_count)

        except (ClientError, ValueError, KeyError) as e:
            _LOGGER.error("Error updating alarms: %s", e)

        # handle ucr data
        data[D_UCR] = ucr

        # handle ucr_default data
        data[D_UCR_DEFAULT] = ucr_default

        # handle active ucr data
        data[D_UCR_ACTIVE] = ucr_active

        # handle ts data
        data[D_TS] = ts

        # handle user data
        data[D_USER] = user

        # handle cluster data
        data[D_CLUSTER] = cluster

        # handle monitor data
        data[D_MONITOR] = monitor

        # handle news data
        data[D_NEWS] = news

        # handle events data
        data[D_EVENTS] = events

        # handle dm data
        data[D_DM] = dm

        # handle message channel data
        data[D_MESSAGE_CHANNEL] = message_channel

        # handle message data
        data[D_MESSAGE] = message

        # handle monitor data
        data[D_LOCALMONITOR] = localmonitor

        # handle statusplan data
        data[D_STATUSPLAN] = statusplan

    except (ClientError, ValueError, KeyError) as e:
        _LOGGER.error("Error in data request: %s", e)

    return data
