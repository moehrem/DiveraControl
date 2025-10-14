"""Updates and processes data from Divera API."""

import logging
from typing import Any

from aiohttp import ClientError
from homeassistant.exceptions import HomeAssistantError

from .const import (
    D_ALARM,
    D_CLUSTER,
    D_DM,
    D_EVENTS,
    D_LOCALMONITOR,
    D_MESSAGE,
    D_MESSAGE_CHANNEL,
    D_MONITOR,
    D_NEWS,
    D_STATUS,
    D_STATUSPLAN,
    D_TS,
    D_UCR,
    D_UCR_ACTIVE,
    D_UCR_DEFAULT,
    D_USER,
    D_VEHICLE,
    D_DATA,
    D_OPEN_ALARMS,
)
from .divera_api import D_UCR, DiveraAPI

_LOGGER = logging.getLogger(__name__)


def _convert_empty_lists_to_dicts(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert empty lists to empty dicts in nested structures.

    Divera API sometimes returns empty lists instead of empty dicts for
    collections like alarm.items or cluster.vehicle when no data is present.

    Args:
        data: Dictionary potentially containing empty lists

    Returns:
        Dictionary with empty lists converted to empty dicts

    """
    result = {}
    for key, value in data.items():
        if value == []:
            # Convert empty list to empty dict
            result[key] = {}
        elif isinstance(value, dict):
            # Recursively process nested dicts
            result[key] = _convert_empty_lists_to_dicts(value)
        else:
            # Keep other values as-is
            result[key] = value
    return result


async def update_data(api: DiveraAPI, cluster_data: dict[str, Any]) -> dict[str, Any]:
    """Update operational data from the Divera API.

    This method fetches all short live data from the Divera API and updates
    the given data dictionary accordingly.

    Args:
        api (DiveraAPI): The API instance used to communicate with Divera.
        cluster_data (dict): A dictionary to store and update Divera operational data.

    Exceptions:
        Logs errors for network issues, invalid data, or missing keys in API responses.
        Sets alarm and vehicle data to empty if any issues occur.

    Returns:
        cluster_data (dict): The updated data dictionary with the latest Divera information.

    """

    # init structure on first call
    if not cluster_data:
        cluster_data = {
            D_UCR: {},
            D_UCR_DEFAULT: {},
            D_UCR_ACTIVE: {},
            D_TS: {},
            D_USER: {},
            D_STATUS: {},
            D_CLUSTER: {},
            D_MONITOR: {},
            D_ALARM: {},
            D_NEWS: {},
            D_EVENTS: {},
            D_DM: {},
            D_MESSAGE_CHANNEL: {},
            D_MESSAGE: {},
            D_LOCALMONITOR: {},
            D_STATUSPLAN: {},
        }

    # request divera data
    try:
        raw_ucr_data = await api.get_ucr_data()

        if not raw_ucr_data.get("success", False):
            _LOGGER.error(
                "Unexpected data format or API request failed: %s",
                raw_ucr_data,
            )
            return cluster_data

    except (ClientError, ValueError, KeyError) as e:
        _LOGGER.error("Error in data request: %s", e)
        return cluster_data

    # set local data
    raw_cluster: dict[str, Any] = raw_ucr_data.get(D_DATA, {}).get(D_CLUSTER, {})

    # update data if new data available
    key = None
    try:
        for key in cluster_data:
            raw_value = raw_ucr_data.get(D_DATA, {}).get(key)

            # Skip if no data
            if raw_value is None:
                cluster_data[key] = {}
                continue

            # If raw_value is a dict, recursively convert empty lists to dicts
            if isinstance(raw_value, dict):
                cluster_data[key] = _convert_empty_lists_to_dicts(raw_value)
            # If raw_value is an empty list, convert to empty dict
            elif raw_value == []:
                cluster_data[key] = {}
            else:
                cluster_data[key] = raw_value

            _LOGGER.debug(
                "Successfully updated key '%s', check diagnostics for data details",
                key,
            )
    except (KeyError, AttributeError) as e:
        _LOGGER.error("Error updating Divera data for key '%s', error: '%s'", key, e)
    except Exception:
        _LOGGER.exception("Unexpected error while updating data from Divera")

    # adding properties to vehicle
    try:
        for key in raw_cluster.get(D_VEHICLE, {}):
            try:
                raw_vehicle_property = await api.get_vehicle_property(key)
            except HomeAssistantError as e:
                _LOGGER.error(
                    "Error fetching vehicle property for vehicle id '%s': %s", key, e
                )
                continue

            if raw_vehicle_property:
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
                    _LOGGER.error(
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
        # Use normalized data from cluster_data instead of raw alarm data
        alarm_items = cluster_data.get(D_ALARM, {}).get("items", {})
        if alarm_items:
            open_alarms = sum(
                1
                for alarm_details in alarm_items.values()
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

    return cluster_data
