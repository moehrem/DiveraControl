"""Updates and processes data from Divera API."""

import logging
from typing import Any

from aiohttp import ClientError

from .const import D_ALARM, D_CLUSTER, D_DATA, D_OPEN_ALARMS, D_UCR_ID, D_VEHICLE
from .divera_api import DiveraAPI

_LOGGER = logging.getLogger(__name__)


async def update_data(
    api: DiveraAPI,
    cluster_data: dict[str, Any],
    admin_data: dict[str, Any],
) -> None:
    """Update operational data from the Divera API.

    This method fetches all short live data from the Divera API and updates
    the given data dictionary accordingly.

    Args:
        api (DiveraAPI): The API instance used to communicate with Divera.
        cluster_data (dict): A dictionary to store and update Divera operational data.
        admin_data (dict): A dictionary to store and update Divera admin data.

    Exceptions:
        Logs errors for network issues, invalid data, or missing keys in API responses.
        Sets alarm and vehicle data to empty if any issues occur.

    Returns:
        None

    """

    # request divera data
    try:
        ucr_id = admin_data[D_UCR_ID]
        raw_ucr_data = await api.get_ucr_data(ucr_id)

        if not raw_ucr_data.get("success", False):
            _LOGGER.error(
                "Unexpected data format or API request failed: %s",
                raw_ucr_data,
            )
            return

    except (ClientError, ValueError, KeyError) as e:
        _LOGGER.error("Error in data request: %s", e)
        return

    # set local data
    cluster = raw_ucr_data.get(D_DATA, {}).get(D_CLUSTER, {})
    alarm = raw_ucr_data.get(D_DATA, {}).get(D_ALARM, {})

    # update data if new data available
    key = None
    try:
        for key in cluster_data:
            cluster_data[key] = raw_ucr_data.get(D_DATA, {}).get(key, {})
            _LOGGER.debug(
                "Sucessfully updated key '%s', check diagnostics for data details",
                key,
            )
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
                        D_CLUSTER in cluster_data
                        and D_VEHICLE in cluster_data[D_CLUSTER]
                    ):
                        cluster_data[D_CLUSTER][D_VEHICLE].setdefault(key, {}).update(
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
        _LOGGER.error("Error fetching vehicle properties, error: '%s'", e)
    except Exception:
        _LOGGER.exception("Unexpected error while processing vehicle properties")

    # handle open alarms
    try:
        if alarm.get("items", {}):
            open_alarms = sum(
                1
                for alarm_details in alarm.get("items", {}).values()
                if not alarm_details.get("closed", True)
            )
            cluster_data.setdefault(D_ALARM, {})[D_OPEN_ALARMS] = open_alarms
        else:
            open_alarms = 0

        _LOGGER.debug("Open alarms updated: %s", open_alarms)

    except (KeyError, AttributeError) as e:
        _LOGGER.error("Error processing alarm data: %s", e)
    except Exception:
        _LOGGER.exception("Unexpected error while processing alarms")
