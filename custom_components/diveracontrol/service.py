"""Create, handle and register all services.

Services still work with "cluster_id" instead of "ucr_id", as its less abstract and thus more user friendly.

"""

import functools
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import D_ALARM, D_MESSAGE_CHANNEL
from .utils import get_api_instance, get_coordinator_data, handle_entity

LOGGER = logging.getLogger(__name__)


async def handle_post_vehicle_status(
    hass: HomeAssistant,
    call: dict,
) -> None:
    """POST set vehicle fms-status.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    vehicle_id = call.data.get("vehicle_id")

    api_instance = get_api_instance(hass, vehicle_id)

    payload = {
        k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
    }

    ok_status = await api_instance.post_vehicle_status(vehicle_id, payload)
    if not ok_status:
        error_msg = f"Failed to set vehicle status for vehicle {vehicle_id}, check logs for details."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    await handle_entity(hass, call, "post_vehicle_status")


async def handle_post_alarm(
    hass: HomeAssistant,
    call: dict,
) -> None:
    """POST create an alarm.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    cluster_id = call.data.get("cluster_id")
    group = call.data.get("group")
    user_cluster_relation = call.data.get("user_cluster_relation")
    notification_type = 4 if user_cluster_relation else 3 if group else 2

    api_instance = get_api_instance(hass, cluster_id)

    payload = {
        "Alarm": {
            k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
        },
        "notification_type": notification_type,
    }

    ok_status = await api_instance.post_alarms(payload)
    if not ok_status:
        error_msg = "Failed to post alarm, please check logs for details."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    # no handle_entity(), as data will update from Divera


async def handle_put_alarm(
    hass: HomeAssistant,
    call: dict,
) -> None:
    """PUT change an existing alarm.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    alarm_id = call.data.get("alarm_id")

    api_instance = get_api_instance(hass, alarm_id)

    payload = {
        "Alarm": {
            key: value
            for key, value in call.data.items()
            if key != "cluster_id" and value is not None
        }
    }

    ok_status = await api_instance.put_alarms(alarm_id, payload)
    if not ok_status:
        error_msg = f"Failed to change alarm {alarm_id}, check logs for details"
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    await handle_entity(hass, call, "put_alarm")


async def handle_post_close_alarm(
    hass: HomeAssistant,
    call: dict,
):
    """POST close an existing alarm.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    alarm_id = call.data.get("alarm_id")

    api_instance = get_api_instance(hass, alarm_id)

    payload = {
        "Alarm": {
            k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
        }
    }

    ok_status = await api_instance.post_close_alarm(payload, alarm_id)
    if not ok_status:
        error_msg = f"Failed to close alarm {alarm_id}, check logs for details."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    await handle_entity(hass, call, "post_close_alarm")


async def handle_post_message(
    hass: HomeAssistant,
    call: dict,
) -> None:
    """Post message for alarm messenger.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    message_channel_id = call.data.get("message_channel_id")
    alarm_id = call.data.get("alarm_id")

    coordinator_data = get_coordinator_data(hass, alarm_id)
    message_channel_items = coordinator_data.get(D_MESSAGE_CHANNEL, {}).get("items", {})
    api_instance = get_api_instance(hass, alarm_id)

    # If neither message_channel_id nor alarm_id is provided, abort
    if not message_channel_id and not alarm_id:
        error_msg = "Either 'message_channel_id' or 'alarm_id' must be provided, but neither was given."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    # Determine message_channel_id from alarm_id if not given
    if not message_channel_id and alarm_id:
        message_channel_id = (
            coordinator_data.get(D_ALARM, {})
            .get(str(alarm_id), {})
            .get("message_channel_id")
        )

    # If still no valid message_channel_id, abort
    if not message_channel_id:
        error_msg = f"No message channel found for alarm_id {alarm_id}."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    # Validate message_channel_id
    if str(message_channel_id) not in message_channel_items:
        error_msg = (
            f"Channel ID {message_channel_id} is invalid or you lack permissions."
        )
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    payload = {
        "Message": {
            "message_channel_id": message_channel_id,
            "text": call.data["text"],
        }
    }

    ok_status = await api_instance.post_message(payload)
    if not ok_status:
        error_msg = "Failed to send message, please check logs."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None


async def handle_post_using_vehicle_property(
    hass: HomeAssistant,
    call: dict,
) -> None:
    """Set individual properties of a specific vehicle.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    vehicle_id = call.data.get("vehicle_id")

    api_instance = get_api_instance(hass, vehicle_id)

    payload = {
        k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
    }

    ok_status = await api_instance.post_using_vehicle_property(vehicle_id, payload)
    if not ok_status:
        error_msg = f"Failed to post vehicle properties for Vehicle-ID {vehicle_id}, check logs for details."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    await handle_entity(hass, call, "post_using_vehicle_property")


async def handle_post_using_vehicle_crew(
    hass: HomeAssistant,
    call: dict,
) -> None:
    """Add, remove, reset the crew of a specific vehicle.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    vehicle_id = call.data.get("vehicle_id")
    mode = call.data.get("mode")

    api_instance = get_api_instance(hass, vehicle_id)

    if mode == "add" and not call.data.get("crew"):
        error_msg = "No crew provided for mode 'add'."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    if mode == "remove" and not call.data.get("crew"):
        error_msg = "No crew provided for mode 'remove'."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    match mode:
        case "add":
            payload = {"Crew": {"add": call.data.get("crew")}}

        case "remove":
            payload = {"Crew": {"remove": call.data.get("crew")}}

        case "reset":
            payload = {}

        case _:
            error_msg = f"Invalid mode '{mode}' for setting vehicle crew, must be 'add', 'remove' or 'reset'."
            LOGGER.error(error_msg)
            raise HomeAssistantError(error_msg) from None

    ok_status = await api_instance.post_using_vehicle_crew(vehicle_id, mode, payload)
    if not ok_status:
        error_msg = f"Failed to post vehicle crew for Vehicle-ID {vehicle_id}, check logs for details."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None

    await handle_entity(hass, call, "post_using_vehicle_crew")


async def async_register_services(
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
        "post_vehicle_status": (
            handle_post_vehicle_status,
            {
                vol.Required("vehicle_id"): cv.positive_int,
                vol.Optional("status"): cv.positive_int,
                vol.Optional("status_id"): cv.positive_int,
                vol.Optional("status_note"): cv.string,
                vol.Optional("lat"): cv.positive_float,
                vol.Optional("lng"): cv.positive_float,
            },
        ),
        "post_alarm": (
            handle_post_alarm,
            {
                vol.Required("cluster_id"): cv.string,
                vol.Required("title"): cv.string,
                vol.Required("notification_type"): cv.positive_int,
                vol.Optional("foreign_id"): cv.string,
                vol.Optional("priority"): cv.boolean,
                vol.Optional("text"): cv.string,
                vol.Optional("address"): cv.string,
                vol.Optional("lat"): cv.positive_float,
                vol.Optional("lng"): cv.positive_float,
                vol.Optional("response_time"): cv.positive_int,
                vol.Optional("send_push"): cv.boolean,
                vol.Optional("send_sms"): cv.boolean,
                vol.Optional("send_call"): cv.boolean,
                vol.Optional("send_mail"): cv.boolean,
                vol.Optional("send_pager"): cv.boolean,
                vol.Optional("closed"): cv.boolean,
                vol.Optional("notification_filter_access"): cv.boolean,
                vol.Optional("group"): cv.string,
                vol.Optional("user_cluster_relation"): cv.string,
                vol.Optional("notification_filter_vehicle"): cv.boolean,
                vol.Optional("vehicle"): cv.string,
                vol.Optional("notification_filter_status"): cv.boolean,
                vol.Optional("status"): cv.string,
            },
        ),
        "put_alarm": (
            handle_put_alarm,
            {
                vol.Required("alarm_id"): cv.positive_int,
                vol.Required("title"): cv.string,
                vol.Required("notification_type"): cv.positive_int,
                vol.Optional("foreign_id"): cv.string,
                vol.Optional("alarmcode_id"): cv.positive_int,
                vol.Optional("priority"): cv.boolean,
                vol.Optional("text"): cv.string,
                vol.Optional("address"): cv.string,
                vol.Optional("lat"): cv.positive_float,
                vol.Optional("lng"): cv.positive_float,
                vol.Optional("report"): cv.string,
                vol.Optional("private_mode"): cv.boolean,
                vol.Optional("send_push"): cv.boolean,
                vol.Optional("send_sms"): cv.boolean,
                vol.Optional("send_call"): cv.boolean,
                vol.Optional("send_mail"): cv.boolean,
                vol.Optional("send_pager"): cv.boolean,
                vol.Optional("response_time"): cv.positive_int,
                vol.Optional("closed"): cv.boolean,
                vol.Optional("ts_publish"): cv.positive_int,
                vol.Optional("notification_filter_access"): cv.boolean,
                vol.Optional("group"): cv.string,
                vol.Optional("user_cluster_relation"): cv.string,
                vol.Optional("notification_filter_vehicle"): cv.boolean,
                vol.Optional("vehicle"): cv.string,
                vol.Optional("notification_filter_status"): cv.boolean,
                vol.Optional("status"): cv.string,
            },
        ),
        "post_close_alarm": (
            handle_post_close_alarm,
            {
                vol.Required("alarm_id"): cv.positive_int,
                vol.Optional("closed"): cv.boolean,
                vol.Optional("report"): cv.string,
            },
        ),
        "post_message": (
            handle_post_message,
            {
                vol.Required("message_channel_id"): vol.Any(None, cv.positive_int),
                vol.Required("alarm_id"): vol.Any(None, cv.positive_int),
                vol.Optional("text"): cv.string,
            },
        ),
        "post_using_vehicle_property": (
            handle_post_using_vehicle_property,
            {
                vol.Required("vehicle_id"): cv.positive_int,
                vol.Extra: vol.Any(
                    vol.Coerce(str), vol.Coerce(int), vol.Coerce(float), None
                ),
            },
        ),
        "post_using_vehicle_crew": (
            handle_post_using_vehicle_crew,
            {
                vol.Required("vehicle_id"): cv.positive_int,
                vol.Required("mode"): cv.string,
                vol.Optional("crew"): cv.ensure_list,
            },
        ),
    }

    for service_name, (handler, schema) in service_definitions.items():
        hass.services.async_register(
            domain,
            service_name,
            functools.partial(handler, hass),
            schema=vol.Schema(schema),
        )
