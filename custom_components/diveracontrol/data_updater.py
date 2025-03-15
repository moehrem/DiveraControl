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
from typing import Any
from .api import DiveraAPI

from aiohttp import ClientError

from .const import (
    # data
    D_DATA,
    D_OPEN_ALARMS,
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
    D_VEHICLE,
    D_UCR_ID,
)

_LOGGER = logging.getLogger(__name__)


async def update_operational_data(
    api: DiveraAPI, changing_data: dict[str, Any], admin_data: dict[str, Any]
) -> dict[str, Any]:
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
        data (dict): A dictionary to store and update alarm and vehicle data.

    """

    def check_timestamp(old_data, new_data):
        """Check if new data has a more recent timestamp than old data."""
        try:
            old_ts = old_data.get("ts", 0)
            if old_ts == 0:
                return True

            new_ts = new_data.get("ts", 0)

        except AttributeError as e:
            _LOGGER.debug("Timestamp check failed due to missing attributes: %s", e)
            return True

        else:
            return new_ts > old_ts

    # request divera data
    try:
        ucr_id = admin_data[D_UCR_ID]
        raw_ucr_data = await api.get_ucr_data(ucr_id)

        if not raw_ucr_data.get("success", False):
            _LOGGER.error(
                "Unexpected data format or API request failed: %s",
                raw_ucr_data,
            )
            return changing_data

    except (ClientError, ValueError, KeyError) as e:
        _LOGGER.error("Error in data request: %s", e)
        return changing_data

    # set local data
    cluster = raw_ucr_data.get(D_DATA, {}).get(D_CLUSTER, {})
    alarm = raw_ucr_data.get(D_DATA, {}).get(D_ALARM, {})

    # update data if new data available
    try:
        for key in changing_data:
            new_data = raw_ucr_data.get(D_DATA, {}).get(key, {})
            if check_timestamp(changing_data.get(key), new_data):
                changing_data[key] = new_data
                _LOGGER.debug("%s data updated: %s", key, new_data)
    except (KeyError, AttributeError) as e:
        _LOGGER.error("Error updating Divera data for key '%s', error: '%s'", key, e)
    except Exception:
        _LOGGER.exception("Unexpected error while updating data from Divera")

    # adding properties to vehicle
    try:
        for key in cluster.get(D_VEHICLE, {}):
            raw_vehicle_property = await api.get_vehicle_property(key)

            if raw_vehicle_property is not False:
                vehicle_property = raw_vehicle_property.get(D_DATA, {})
                if isinstance(vehicle_property, dict):
                    if (
                        D_CLUSTER in changing_data
                        and D_VEHICLE in changing_data[D_CLUSTER]
                    ):
                        changing_data[D_CLUSTER][D_VEHICLE].setdefault(key, {}).update(
                            vehicle_property
                        )

                else:
                    _LOGGER.warning(
                        "Unexpected vehicle property format for '%s': %s",
                        key,
                        vehicle_property,
                    )

                _LOGGER.debug(
                    "Vehicle properties updated for '%s', properties: %s",
                    key,
                    vehicle_property,
                )
    except (KeyError, AttributeError) as e:
        _LOGGER.error(
            "Error fetching vehicle properties for vehicle '%s', error: '%s'", key, e
        )
    except Exception:
        _LOGGER.exception("Unexpected error while processing vehicle properties")

    # handle open alarms
    try:
        if alarm:
            open_alarms = sum(
                1
                for alarm_details in alarm.get("items", {}).values()
                if not alarm_details.get("closed", True)
            )
            changing_data.setdefault(D_ALARM, {})[D_OPEN_ALARMS] = open_alarms
        else:
            open_alarms = 0

        _LOGGER.debug("Open alarms updated: %s", open_alarms)

    except (KeyError, AttributeError) as e:
        _LOGGER.error("Error processing alarm data: %s", e)
    except Exception:
        _LOGGER.exception("Unexpected error while processing alarms")

    return changing_data
