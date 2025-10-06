"""Create, handle and register all services.

Service handling functions are in the form of handle_<service_name>.
Each function includes a check for mandatory fields, extracts the
payload and calls the respective API function. If successful, it will
handle the entity and return the result.

All services are registered with async_register_services. They are not
registered with a schema but based on services.yaml. This is needed due
to easier implementation of device actions.
Thats why its necessary to check for mandatory fields in each function.

"""

from datetime import datetime
import functools
import logging
from typing import Any

import voluptuous as vol

from homeassistant.helpers import device_registry as dr
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import D_ALARM, D_MESSAGE_CHANNEL, D_UCR_ID, DOMAIN
from .utils import get_api_instances, get_coordinator_data, handle_entity
from .coordinator import DiveraCoordinator

LOGGER = logging.getLogger(__name__)


def _extract_news(data: dict, notification_type: int) -> dict:
    """Extract news data from call-data of service 'post_news'.

    Args:
        data (dict): service call data.
        notification_type (int): notification_type.

    Returns:
        dict: news_data

    """

    news_data: dict = {}
    for key, value in data.items():
        if key == "notification_type":
            news_data["notification_type"] = notification_type
        elif key in ("group", "user_cluster_relation"):
            val = value
            if isinstance(val, list):
                news_data[key] = val
            elif isinstance(val, str):
                news_data[key] = [int(s.strip()) for s in val.split(",") if s.strip()]
        elif key == "cluster_id":
            news_data["cluster_id"] = int(value)
        elif key in ("NewsSurvey_ts_response", "ts_archive"):
            unix_dt = datetime.fromisoformat(value)
            news_data[key] = unix_dt
        else:
            news_data[key] = value
    return news_data


def _extract_survey(data: dict) -> dict:
    """Extract survey data from call-data of service "post_news.

    Args:
        data (dict): service call data.

    Returns:
        dict: survey_data

    """

    survey_data: dict = {}
    for key, value in data.items():
        if not key.startswith("NewsSurvey_"):
            continue
        survey_key = key[len("NewsSurvey_") :]
        if survey_key in ("answers", "sorting") and isinstance(value, str):
            survey_data[survey_key] = [s.strip() for s in value.split(",") if s.strip()]
        else:
            survey_data[survey_key] = value
    return survey_data


async def _get_coordinator_from_device_id(
    hass: HomeAssistant,
    device_id: str,
) -> DiveraCoordinator | None:
    """Get coordinator from device_id.

    Args:
        hass: Home Assistant instance
        device_id: Device ID from service call

    Returns:
        DiveraCoordinator instance or None if not found
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device:
        return None

    # Get config entry ID from device
    entry_id = next(iter(device.config_entries), None)
    if not entry_id:
        return None

    # Get config entry
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry or entry.domain != DOMAIN:
        return None

    # Get coordinator from hass.data
    ucr_id = entry.data.get(D_UCR_ID)
    if not ucr_id:
        return None

    return hass.data[DOMAIN][ucr_id]["coordinator"]


async def handle_post_vehicle_status(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """POST set vehicle fms-status.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict[str, Any]): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    vehicle_id: int = call.data.get("vehicle_id") or 0

    if not vehicle_id:
        raise HomeAssistantError("No vehicle_id provided.")

    # get api instances
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # create payload
    payload: dict[str, Any] = {
        k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
    }

    # call api function and handle entity
    for api_instance in api_instances:
        ok_status = await api_instance.post_vehicle_status(vehicle_id, payload)
        if not ok_status:
            error_msg = f"Failed to set vehicle status for vehicle {vehicle_id}, check logs for details."
            LOGGER.error(error_msg)

        await handle_entity(
            hass, call, "post_vehicle_status", api_instance.ucr_id, vehicle_id
        )


async def handle_post_alarm(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """POST create an alarm.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    title = call.data.get("title") or ""
    notification_type = call.data.get("notification_type") or 0

    if not title:
        raise HomeAssistantError("No title provided for alarm.")
    if not notification_type:
        raise HomeAssistantError("No notification type provided for alarm.")

    # get api instance
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # create payload
    payload: dict[str, Any] = {
        "Alarm": {
            k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
        },
        "notification_type": notification_type,
    }

    # call api function and handle entity
    for api_instance in api_instances:
        ok_status = await api_instance.post_alarms(payload)
        if not ok_status:
            error_msg = "Failed to post alarm, please check logs for details."
            LOGGER.error(error_msg)

        # no handle_entity(), as data needs to be updated from Divera first


async def handle_put_alarm(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """PUT change an existing alarm.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    alarm_id: str = call.data.get("alarm_id") or ""
    title: str = call.data.get("title") or ""
    notification_type: int = call.data.get("notification_type") or 0

    if not alarm_id:
        raise HomeAssistantError("No alarm_id provided for update.")
    if not title:
        raise HomeAssistantError("No title provided for update.")
    if not notification_type:
        raise HomeAssistantError("No notification type provided for update.")

    # get api instance
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # create payload
    payload: dict[str, Any] = {
        "Alarm": {
            key: value
            for key, value in call.data.items()
            if key != "cluster_id" and value is not None
        }
    }

    # call api function and handle entity
    for api_instance in api_instances:
        ok_status = await api_instance.put_alarms(alarm_id, payload)
        if not ok_status:
            error_msg = f"Failed to change alarm {alarm_id}, check logs for details"
            LOGGER.error(error_msg)

        await handle_entity(hass, call, "put_alarm", api_instance.ucr_id, alarm_id)


async def handle_post_close_alarm(
    hass: HomeAssistant,
    call: ServiceCall,
):
    """POST close an existing alarm.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    alarm_id: str = call.data.get("alarm_id") or ""
    if not alarm_id:
        raise HomeAssistantError("No alarm_id provided for closing.")

    # get api instance
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # create payload
    payload: dict[str, Any] = {
        "Alarm": {
            k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
        }
    }

    # call api function and handle entity
    for api_instance in api_instances:
        ok_status = await api_instance.post_close_alarm(payload, alarm_id)
        if not ok_status:
            error_msg = f"Failed to close alarm {alarm_id}, check logs for details."
            LOGGER.error(error_msg)

        await handle_entity(
            hass, call, "post_close_alarm", api_instance.ucr_id, alarm_id
        )


async def handle_post_message(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """Post message for alarm messenger.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    message_channel_id: int = call.data.get("message_channel_id") or 0
    alarm_id: str = str(call.data.get("alarm_id")) or ""

    if message_channel_id and alarm_id:
        raise HomeAssistantError(
            "Either 'message channel id' or 'alarm id' must be provided, not both."
        )

    if not message_channel_id and not alarm_id:
        raise HomeAssistantError(
            "Either 'message channel id' or 'alarm id' must be provided."
        )

    # Determine message_channel_id from alarm_id if not given
    if not message_channel_id and alarm_id:
        coordinator = (
            await _get_coordinator_from_device_id(hass, call.data.get("device_id", []))
            if call.data.get("device_id")
            else None
        )
        if coordinator:
            message_channel_id = (
                coordinator.data.get(D_ALARM, {})
                .get("items", {})
                .get(alarm_id, {})
                .get("message_channel_id", 0)
            )

    # If still no valid message_channel_id, abort
    if not message_channel_id:
        error_msg = f"No message channel found for alarm id '{alarm_id}'. Check if there is a message channel for that alarm."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    # get api instances
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # create payload
    payload: dict[str, Any] = {
        "Message": {
            "message_channel_id": message_channel_id,
            "text": call.data["text"],
        }
    }

    # call api function and handle entity
    for api_instance in api_instances:
        ok_status = await api_instance.post_message(payload)
        if not ok_status:
            error_msg = "Failed to send message, please check logs."
            LOGGER.error(error_msg)

        # no handle entity as new data needs to be fetched from Divera first


async def handle_post_using_vehicle_property(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """Set individual properties of a specific vehicle.

    Searches for vehicle_id in entity attributes. Accepts a single entity aka vehicle only.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    vehicle_id = call.data.get("vehicle")
    payload = call.data.get("properties", {})  # ✅ Automatisch als dict geparst

    if not isinstance(payload, dict):
        raise ServiceValidationError("Properties must be a dictionary")

    # get api instance
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # create payload
    # payload: dict[str, Any] = {
    #     k: v
    #     for k, v in properties.items()
    #     if k not in {"device_id", "entity_id"} and v is not None
    # }

    # call api function and handle entity
    for api_instance in api_instances:
        ok_status = await api_instance.post_using_vehicle_property(vehicle_id, payload)
        if not ok_status:
            error_msg = f"Failed to post vehicle properties for Vehicle-ID {vehicle_id}, check logs for details."
            LOGGER.error(error_msg)

        await handle_entity(
            hass, call, "post_using_vehicle_property", api_instance.ucr_id, vehicle_id
        )


async def handle_post_using_vehicle_crew(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """Add, remove, reset the crew of a specific vehicle.

    Searches for vehicle_id in entity attributes. Accepts only one entity aka vehicle.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    mode: str = call.data.get("mode", "")
    vehicle_id: int = call.data.get("vehicle")

    if not mode:
        raise HomeAssistantError("No mode provided for setting vehicle crew.")

    # get api instance
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # check modes and input
    if mode in {"add", "remove"} and not call.data.get("crew"):
        raise HomeAssistantError(f"No crew provided for mode '{mode}'.")

    # create payload
    payload: dict[str, Any] = {}
    match mode:
        case "add":
            payload = {"Crew": {"add": call.data.get("crew")}}

        case "remove":
            payload = {"Crew": {"remove": call.data.get("crew")}}

        case "reset":
            payload = {}

        case _:
            raise HomeAssistantError(
                f"Invalid mode '{mode}' for setting vehicle crew, must be 'add', 'remove' or 'reset'."
            )

    for api_instance in api_instances:
        ok_status = await api_instance.post_using_vehicle_crew(
            vehicle_id, mode, payload
        )
        if not ok_status:
            error_msg = f"Failed to post vehicle crew for Vehicle-ID {vehicle_id}, check logs for details."
            LOGGER.error(error_msg)

        # await handle_entity(
        #     hass, call, "post_using_vehicle_crew", api_instance.ucr_id, vehicle_id
        # )


async def handle_post_news(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """Add, remove, reset the crew of a specific vehicle.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    title: str = call.data.get("title", "")
    notification_type: int = call.data.get("notification_type", 0)

    if not title and not notification_type:
        raise HomeAssistantError("No title or notification_type provided.")

    # get api instance
    device_ids = call.data.get("device_id", [])
    entity_ids = call.data.get("entity_id", [])
    api_instances = get_api_instances(hass, device_ids, entity_ids)

    if not api_instances:
        raise HomeAssistantError("No Divera unit found for target.")

    # create payload
    payload: dict[str, Any] = {}

    survey_flag = call.data.get("survey") or False

    news_data = {}
    survey_data = {}

    if survey_flag:
        survey_data = _extract_survey(call.data)
        news_data = _extract_news(call.data, notification_type)
    else:
        news_data = _extract_news(call.data, notification_type)

    payload = {
        "News": news_data,
        "NewsSurvey": survey_data,
    }

    # call api function and handle entity
    for api_instance in api_instances:
        ok_status = await api_instance.post_news(payload)
        if not ok_status:
            error_msg = "Failed to post new message, check logs for details."
            LOGGER.error(error_msg)

        # no handle entity as new data needs to be fetched from Divera first


def async_register_services(
    hass: HomeAssistant,
    domain: str,
):
    """Register services for DiveraCotnrol.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        domain (str): Domain name for services.

    Returns:
        None

    """

    service_definitions = {
        "post_vehicle_status": handle_post_vehicle_status,
        "post_alarm": handle_post_alarm,
        "put_alarm": handle_put_alarm,
        "post_close_alarm": handle_post_close_alarm,
        "post_message": handle_post_message,
        "post_using_vehicle_property": handle_post_using_vehicle_property,
        "post_using_vehicle_crew": handle_post_using_vehicle_crew,
        "post_news": handle_post_news,
    }

    for service_name, handler in service_definitions.items():
        hass.services.async_register(
            domain,
            service_name,
            functools.partial(handler, hass),
        )
