"""Create, handle and register all services."""

import functools
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import D_ALARM, D_COORDINATOR, D_MESSAGE_CHANNEL, DOMAIN

LOGGER = logging.getLogger(__name__)


def get_api_instance(hass: HomeAssistant, cluster_id: str):
    """Holt die API-Instanz für die gegebene cluster_id oder wirft eine Exception."""
    try:
        api_instance = hass.data[DOMAIN][str(cluster_id)]["api"]
        return api_instance

    except KeyError:
        error_message = f"API-instance or API-key not found for cluster-ID {cluster_id}"
        LOGGER.error(error_message)
        raise HomeAssistantError(error_message) from None


def get_coordinator_data(hass: HomeAssistant, cluster_id: str) -> dict[str, any]:
    """Holt die Koordinatordaten für die gegebene cluster_id oder wirft eine Exception."""
    coordinator_data = (
        hass.data.get(DOMAIN, {}).get(str(cluster_id), "").get(D_COORDINATOR)
    )

    if not coordinator_data:
        error_msg = f"DiveraCoordinator for cluster {cluster_id} not found."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg)

    return coordinator_data


async def handle_post_vehicle_status(hass: HomeAssistant, call: dict):
    """Setzt den Fahrzeugstatus."""
    cluster_id = call.data.get("cluster_id")
    vehicle_id = call.data.get("vehicle_id")

    api_instance = get_api_instance(hass, cluster_id)

    payload = {
        k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
    }

    try:
        success = await api_instance.post_vehicle_status(vehicle_id, payload)
        if not success:
            raise HomeAssistantError(
                f"Failed to set vehicle status for vehicle {vehicle_id}, check logs for details."
            )
    except Exception as e:
        error_msg = f"Failed to set vehicle status for vehicle {vehicle_id}: {e}"
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg)


async def handle_post_alarm(hass: HomeAssistant, call: dict):
    """Erstellt einen Alarm."""
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

    try:
        success = await api_instance.post_alarms(payload)
        if not success:
            raise HomeAssistantError(
                "Failed to post alarm, please check logs for details."
            )
    except Exception as e:
        error_msg = f"Failed to post alarm: {e}"
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg)


async def handle_put_alarm(hass: HomeAssistant, call: dict):
    """Change an existing alarm."""
    cluster_id = call.data.get("cluster_id")
    alarm_id = call.data.get("alarm_id")

    api_instance = get_api_instance(hass, cluster_id)

    payload = {
        "Alarm": {
            k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
        }
    }

    try:
        success = await api_instance.put_alarms(payload, alarm_id)
        if not success:
            raise HomeAssistantError(
                f"Failed to change alarm {alarm_id}, check logs for details."
            )
    except Exception as e:
        error_msg = f"Failed to change alarm {alarm_id}: {e}"
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg)


async def handle_post_close_alarm(hass: HomeAssistant, call: dict):
    """Close an existing alarm."""
    cluster_id = call.data.get("cluster_id")
    alarm_id = call.data.get("alarm_id")

    api_instance = get_api_instance(hass, cluster_id)

    payload = {
        "Alarm": {
            k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
        }
    }

    try:
        success = await api_instance.post_close_alarm(payload, alarm_id)
        if not success:
            raise HomeAssistantError(
                f"Failed to close alarm {alarm_id}, check logs for details."
            )
    except Exception as e:
        error_msg = f"Failed to close alarm {alarm_id}: {e}"
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg)


async def handle_post_message(hass: HomeAssistant, call: dict):
    """Post message for alarm messenger."""
    cluster_id = call.data.get("cluster_id")
    message_channel_id = call.data.get("message_channel_id")
    alarm_id = call.data.get("alarm_id")

    coordinator_data = get_coordinator_data(hass, cluster_id)
    message_channel_items = coordinator_data.get(D_MESSAGE_CHANNEL, {}).get("items", {})
    api_instance = get_api_instance(hass, cluster_id)

    # If neither message_channel_id nor alarm_id is provided, abort early
    if not message_channel_id and not alarm_id:
        error_msg = "Either 'message_channel_id' or 'alarm_id' must be provided, but neither was given."
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg)

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
        raise HomeAssistantError(error_msg)

    # Validate message_channel_id
    if str(message_channel_id) not in message_channel_items:
        error_msg = (
            f"Channel ID {message_channel_id} is invalid or you lack permissions."
        )
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg)

    payload = {
        "Message": {
            "message_channel_id": message_channel_id,
            "text": call.data["text"],
        }
    }

    try:
        ok_status = await api_instance.post_message(payload)
        if not ok_status:
            raise HomeAssistantError(
                "Failed to send message, please check logs."
            ) from None
    except Exception as e:
        error_msg = f"Failed to send message: {e}"
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None


async def handle_post_using_vehicle_property(hass: HomeAssistant, call: dict):
    """Set individual properties of a specific vehicle."""
    cluster_id = call.data.get("cluster_id")
    vehicle_id = call.data.get("vehicle_id")

    api_instance = get_api_instance(hass, cluster_id)

    payload = {
        k: v for k, v in call.data.items() if k != "cluster_id" and v is not None
    }

    try:
        success = await api_instance.post_using_vehicle_property(payload, vehicle_id)
        if not success:
            error_msg = f"Failed to post vehicle properties for Vehicle-ID {vehicle_id}, check logs for details."
            raise HomeAssistantError(error_msg) from None
    except Exception as e:
        error_msg = (
            f"Failed to post vehicle properties for Vehicle-ID {vehicle_id}: {e}"
        )
        LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from None


async def async_register_services(hass, domain):
    """Registriert alle Services für die Integration."""
    service_definitions = {
        "post_vehicle_status": (
            handle_post_vehicle_status,
            {
                vol.Required("cluster_id"): cv.positive_int,
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
                vol.Required("cluster_id"): cv.positive_int,
                vol.Required("title"): cv.string,
                vol.Required("notification_type", default=2): cv.positive_int,
                vol.Optional("foreign_id"): cv.string,
                vol.Optional("priority", default=False): cv.boolean,
                vol.Optional("text"): cv.string,
                vol.Optional("address"): cv.string,
                vol.Optional("lat"): cv.positive_float,
                vol.Optional("lng"): cv.positive_float,
                vol.Optional("response_time", default=3600): cv.positive_int,
                vol.Optional("send_push", default=True): cv.boolean,
                vol.Optional("send_sms", default=False): cv.boolean,
                vol.Optional("send_call", default=False): cv.boolean,
                vol.Optional("send_mail", default=False): cv.boolean,
                vol.Optional("send_pager", default=False): cv.boolean,
                vol.Optional("closed", default=False): cv.boolean,
                vol.Optional("notification_filter_access", default=True): cv.boolean,
                vol.Optional("group"): cv.string,
                vol.Optional("user_cluster_relation"): cv.string,
                vol.Optional("notification_filter_vehicle", default=False): cv.boolean,
                vol.Optional("vehicle"): cv.string,
                vol.Optional("notification_filter_status", default=False): cv.boolean,
                vol.Optional("status"): cv.string,
            },
        ),
        "put_alarm": (
            handle_put_alarm,
            {
                vol.Required("cluster_id"): cv.positive_int,
                vol.Required("alarm_id"): cv.positive_int,
                vol.Required("title"): cv.string,
                vol.Required("notification_type", default=2): cv.positive_int,
                vol.Optional("foreign_id"): cv.string,
                vol.Optional("alarmcode_id"): cv.positive_int,
                vol.Optional("priority", default=False): cv.boolean,
                vol.Optional("text"): cv.string,
                vol.Optional("address"): cv.string,
                vol.Optional("lat"): cv.positive_float,
                vol.Optional("lng"): cv.positive_float,
                vol.Optional("report"): cv.string,
                vol.Optional("private_mode", default=False): cv.boolean,
                vol.Optional("send_push", default=True): cv.boolean,
                vol.Optional("send_sms", default=False): cv.boolean,
                vol.Optional("send_call", default=False): cv.boolean,
                vol.Optional("send_mail", default=False): cv.boolean,
                vol.Optional("send_pager", default=False): cv.boolean,
                vol.Optional("response_time", default=3600): cv.positive_int,
                vol.Optional("closed", default=False): cv.boolean,
                vol.Optional("ts_publish"): cv.positive_int,
                vol.Optional("notification_filter_access", default=True): cv.boolean,
                vol.Optional("group"): cv.string,
                vol.Optional("user_cluster_relation"): cv.string,
                vol.Optional("notification_filter_vehicle", default=False): cv.boolean,
                vol.Optional("vehicle"): cv.string,
                vol.Optional("notification_filter_status", default=False): cv.boolean,
                vol.Optional("status"): cv.string,
            },
        ),
        "post_close_alarm": (
            handle_post_close_alarm,
            {
                vol.Required("cluster_id"): cv.positive_int,
                vol.Required("alarm_id"): cv.positive_int,
                vol.Optional("closed"): cv.boolean,
                vol.Optional("report"): cv.string,
            },
        ),
        "post_message": (
            handle_post_message,
            {
                vol.Required("cluster_id"): cv.positive_int,
                vol.Optional("message_channel_id", default=None): vol.Any(
                    None, cv.positive_int
                ),
                vol.Optional("alarm_id", default=None): vol.Any(None, cv.positive_int),
                vol.Optional("text"): cv.string,
            },
        ),
        "post_using_vehicle_property": (
            handle_post_using_vehicle_property,
            {
                vol.Required("cluster_id"): cv.positive_int,
                vol.Required("vehicle_id"): cv.positive_int,
                vol.Extra: vol.Any(
                    vol.Coerce(str), vol.Coerce(int), vol.Coerce(float), None
                ),
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
