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

from collections.abc import Callable
import functools
import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import D_ALARM, DOMAIN
from .data_normalizer import normalize_service_call_data
from .utils import get_coordinator_key_from_device, get_translation, handle_entity

_LOGGER = logging.getLogger(__name__)

POST_VEHICLE_VALIDATION_RULES = {
    "vehicle_id": {
        "condition": lambda data: not data.get("vehicle_id"),
        "error_key": "no_vehicle_id",
    }
}

# Base alarm validation rules (shared)
_ALARM_BASE_VALIDATION_RULES = {
    "title": {
        "condition": lambda data: not data.get("title"),
        "error_key": "no_alarm_title",
    },
    "notification_type": {
        "condition": lambda data: not data.get("notification_type"),
        "error_key": "no_notification_type",
    },
    "groups_for_type_3": {
        "condition": lambda data: data.get("notification_type") == "3"
        and "group" not in data,
        "error_key": "no_groups_selected",
    },
    "users_for_type_4": {
        "condition": lambda data: data.get("notification_type") == "4"
        and "user_cluster_relation" not in data,
        "error_key": "no_users_selected",
    },
    "vehicles_for_filter": {
        "condition": lambda data: data.get("notification_filter_vehicle")
        and "vehicle" not in data,
        "error_key": "no_vehicles_selected",
    },
    "status_for_filter": {
        "condition": lambda data: data.get("notification_filter_status")
        and "status" not in data,
        "error_key": "no_status_selected",
    },
}

POST_ALARM_VALIDATION_RULES = _ALARM_BASE_VALIDATION_RULES

PUT_ALARM_VALIDATION_RULES = {
    "alarm_id": {
        "condition": lambda data: not data.get("alarm_id"),
        "error_key": "no_alarm_id",
    },
    **_ALARM_BASE_VALIDATION_RULES,
}

POST_CLOSE_ALARM_VALIDATION_RULES = {
    "alarm_id": {
        "condition": lambda data: not data.get("alarm_id"),
        "error_key": "no_alarm_id",
    }
}

POST_MESSAGE_VALIDATION_RULES = {
    "both_message_channel_and_alarm_id": {
        "condition": lambda data: data.get("message_channel_id")
        and data.get("alarm_id"),
        "error_key": "both_message_channel_and_alarm_id",
    },
    "no_message_channel_or_alarm_id": {
        "condition": lambda data: not data.get("message_channel_id")
        and not data.get("alarm_id"),
        "error_key": "no_message_channel_or_alarm_id",
    },
}

POST_USING_VEHICLE_CREW_VALIDATION_RULES = {
    "vehicle_id": {
        "condition": lambda data: not data.get("vehicle_id"),
        "error_key": "no_vehicle_id",
    },
    "mode": {
        "condition": lambda data: not data.get("mode"),
        "error_key": "no_mode_provided",
        "translation_placeholders": {"valid_modes": "add, remove, reset"},
    },
    "vehicle_count": {
        "condition": lambda data: len(data.get("vehicle_id", [])) != 1,
        "error_key": "invalid_number_of_vehicles",
        "translation_placeholders": lambda data: {
            "num_vehicles": str(len(data.get("vehicle_id", [])))
        },
    },
    "crew": {
        "condition": lambda data: data.get("mode") in {"add", "remove"}
        and not data.get("crew"),
        "error_key": "no_crew_provided",
        "translation_placeholders": lambda data: {"mode": data.get("mode", "")},
    },
}

POST_NEWS_VALIDATION_RULES = {
    "title": {
        "condition": lambda data: not data.get("title"),
        "error_key": "no_news_title",
    },
    "notification_type": {
        "condition": lambda data: not data.get("notification_type"),
        "error_key": "no_notification_type",
    },
    "groups_for_type_3": {
        "condition": lambda data: data.get("notification_type") == 3
        and not data.get("group"),
        "error_key": "no_groups_selected",
    },
    "users_for_type_4": {
        "condition": lambda data: data.get("notification_type") == 4
        and not data.get("user_cluster_relation"),
        "error_key": "no_users_selected",
    },
    "survey_sorting": {
        "condition": lambda data: data.get("survey")
        and data.get("newssurvey_answers")
        and not data.get("newssurvey_sorting"),
        "error_key": "no_survey_sorting",
    },
}


def _validate_data(data: dict[str, Any], rules: dict[str, dict]) -> None:
    """Validate data against rules.

    Args:
        data: Service call data to validate.
        rules: Validation rules dictionary.

    Raises:
        ServiceValidationError: If any validation fails.
    """
    for rule_name, rule in rules.items():
        if rule["condition"](data):
            # Get translation_placeholders - can be dict or callable
            placeholders = rule.get("translation_placeholders")
            if callable(placeholders):
                placeholders = placeholders(data)

            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=rule["error_key"],
                translation_placeholders=placeholders,
            )


def _extract_news(data: dict[str, Any], notification_type: int) -> dict[str, Any]:
    """Extract news data from call-data of service 'post_news'.

    Args:
        data (dict): service call data.
        notification_type (int): notification_type.

    Returns:
        dict: news_data

    """

    news_data: dict[str, Any] = {}
    for key, value in data.items():
        if key.startswith("newssurvey_"):
            continue
        news_data[key] = value
    return news_data


def _extract_survey(data: dict[str, Any]) -> dict[str, Any]:
    """Extract survey data from call-data of service "post_news.

    Args:
        data (dict): service call data.

    Returns:
        dict: survey_data

    """

    survey_data: dict[str, Any] = {}
    for key, value in data.items():
        if not key.startswith("newssurvey_"):
            continue
        survey_key = key[len("newssurvey_") :]
        survey_data[survey_key] = value
    return survey_data


# async def get_coordinator_key_from_device(
#     hass: HomeAssistant, device_id: str | None
# ) -> Any:  # Replace Any with actual API type
#     """Get API instance for device.

#     Args:
#         hass: Home Assistant instance.
#         device_id: Device ID.

#     Returns:
#         API instance.

#     Raises:
#         ServiceValidationError: If device not found or not loaded.
#     """
#     if not device_id:
#         raise ServiceValidationError(
#             translation_domain=DOMAIN,
#             translation_key="no_device_id",
#         )

#     try:
#         return get_coordinator_key_from_device(hass, device_id, "api")
#     except KeyError as err:
#         _LOGGER.error("Failed to get API instance: %s", err)
#         raise ServiceValidationError(
#             translation_domain=DOMAIN,
#             translation_key="no_divera_unit",
#         ) from err


def _build_payload(
    data: dict[str, Any],
    keys: dict[str, dict[str, Any]] | None = None,
    exclude_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Build API payload from service data.

    Args:
        data: Service call data.
        keys: Dictionary mapping top-level keys to their data sources.
              - Key name → filtered data from `data` parameter (use empty dict {})
              - Key name → specific data dict
              Example: {"Alarm": {}, "Metadata": {"version": "1.0"}}
        exclude_keys: Keys to exclude when filtering from `data`.

    Returns:
        Formatted payload dictionary.

    Examples:
        # Single key with filtered data
        _build_payload(data, keys={"Alarm": {}})
        # Returns: {"Alarm": {filtered_data}}

        # Multiple keys
        _build_payload(
            data,
            keys={"News": {}, "newssurvey": survey_data},
            exclude_keys={k for k in data if k.startswith("newssurvey_")}
        )
        # Returns: {"News": {filtered_data}, "newssurvey": survey_data}

        # Flat payload (no wrapper)
        _build_payload(data)
        # Returns: {filtered_data}

        # Multiple keys with specific data
        _build_payload(
            data,
            keys={
                "Alarm": {},
                "Metadata": {"created_at": datetime.now()},
                "Options": {"priority": True}
            }
        )
    """
    exclude = exclude_keys or set()
    exclude.update({"device_id", "cluster_id"})

    # No keys specified = flat payload
    if not keys:
        return {k: v for k, v in data.items() if k not in exclude and v is not None}

    # Build payload with specified keys
    payload = {}
    filtered_data = None  # Cache filtered data

    for key_name, key_data in keys.items():
        if not key_data:  # Empty dict = use filtered data from `data`
            if filtered_data is None:  # Lazy evaluation
                filtered_data = {
                    k: v for k, v in data.items() if k not in exclude and v is not None
                }
            payload[key_name] = filtered_data
        else:  # Use provided data
            payload[key_name] = key_data

    return payload


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
    data = normalize_service_call_data(call.data)
    _validate_data(data, POST_VEHICLE_VALIDATION_RULES)

    # get api instances
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # create payload
    # payload: dict[str, Any] = {k: v for k, v in data.items() if v is not None}
    payload = _build_payload(data, keys=None)

    # call api function and handle entity
    vehicle_ids: list[int] = data.get("vehicle_id")
    for vehicle in vehicle_ids:
        try:
            await api_instance.post_vehicle_status(vehicle, payload)
            await handle_entity(hass, data, call.service, api_instance.ucr_id, vehicle)
        except HomeAssistantError as err:
            error_msg = await get_translation(
                hass,
                "exceptions",
                "api_post_vehicle_status_failed.message",
                {"vehicle_id": vehicle, "err": str(err)},
            )
            _LOGGER.error(error_msg)
            continue


async def handle_post_alarm(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    """POST create an alarm.

    Check mandatory fields (in case of a device_actions its necessary...),
    normalize data, build payload and trigger api call.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        call (dict): Service call data.

    Returns:
        None

    """

    # check mandatory fields
    data = normalize_service_call_data(call.data)
    _validate_data(data, POST_ALARM_VALIDATION_RULES)

    # get api instance
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # payload: dict[str, Any] = {
    #     "Alarm": {k: v for k, v in data.items() if v is not None},
    # }
    payload = _build_payload(data, keys={"Alarm": {}})

    # call api function and handle entity
    try:
        await api_instance.post_alarms(payload)
        # no handle_entity(), as data needs to be updated from Divera first

    except HomeAssistantError as err:
        error_msg = await get_translation(
            hass,
            "exceptions",
            "api_post_alarm_failed.message",
            {"title": data.get("title"), "err": str(err)},
        )
        _LOGGER.error(error_msg)


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
    data = normalize_service_call_data(call.data)
    _validate_data(data, PUT_ALARM_VALIDATION_RULES)

    # get api instance
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # create payload
    # payload: dict[str, Any] = {
    #     "Alarm": {k: v for k, v in data.items() if v is not None},
    # }
    payload = _build_payload(data, keys={"Alarm": {}})

    # call api function and handle entity
    try:
        alarm_id: Any = data.get("alarm_id")
        await api_instance.put_alarms(alarm_id, payload)
        await handle_entity(hass, data, call.service, api_instance.ucr_id, alarm_id)
    except HomeAssistantError as err:
        error_msg = await get_translation(
            hass,
            "exceptions",
            "api_put_alarm_failed.message",
            {"alarm_id": alarm_id, "err": str(err)},
        )
        _LOGGER.error(error_msg)


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
    data = normalize_service_call_data(call.data)
    _validate_data(data, POST_CLOSE_ALARM_VALIDATION_RULES)

    # get api instance
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # create payload
    payload: dict[str, Any] = {
        "Alarm": {k: v for k, v in data.items() if v is not None}
    }
    payload = _build_payload(data, keys={"Alarm": {}})

    # call api function and handle entity
    try:
        alarm_id: Any = data.get("alarm_id")
        await api_instance.post_close_alarm(payload, alarm_id)
        await handle_entity(hass, data, call.service, api_instance.ucr_id, alarm_id)
    except HomeAssistantError as err:
        error_msg = await get_translation(
            hass,
            "exceptions",
            "api_post_close_alarm_failed.message",
            {"alarm_id": alarm_id, "err": str(err)},
        )
        _LOGGER.error(error_msg)
        return


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
    data = normalize_service_call_data(call.data)
    _validate_data(data, POST_MESSAGE_VALIDATION_RULES)

    # Determine message_channel_id from alarm_id if not given
    device_id = data.get("device_id")
    message_channel_id: int = data.get("message_channel_id") or 0
    alarm_id: int = data.get("alarm_id") or 0
    if not message_channel_id and alarm_id:
        coord_data = (
            get_coordinator_key_from_device(hass, device_id, "data")
            if device_id
            else None
        )
        if coord_data:
            message_channel_id = (
                coord_data.get(D_ALARM, {})
                .get("items", {})
                .get(alarm_id, {})
                .get("message_channel_id", 0)
            )

    # If still no valid message_channel_id, abort
    if not message_channel_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="no_message_channel",
            translation_placeholders={"alarm_id": str(alarm_id)},
        )

    # get api instances
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # create payload
    # payload: dict[str, Any] = {
    #     "Message": {
    #         "message_channel_id": message_channel_id,
    #         "text": data["text"],
    #     }
    # }
    payload = _build_payload(
        data,
        keys={
            "Message": {"message_channel_id": message_channel_id, "text": data["text"]}
        },
    )

    # call api function and handle entity
    try:
        await api_instance.post_message(payload)
        # no handle entity as new data needs to be fetched from Divera first
    except HomeAssistantError as err:
        error_msg = await get_translation(
            hass,
            "exceptions",
            "api_post_message_failed.message",
            {"message_channel_id": message_channel_id, "err": str(err)},
        )
        _LOGGER.error(error_msg)
        return


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

    # check mandatory fields
    data = normalize_service_call_data(call.data)
    _validate_data(data, POST_VEHICLE_VALIDATION_RULES)

    # get api instance
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # call api function and handle entity
    vehicle_ids: list[int] = data.get("vehicle_id") or []

    # payload: dict[str, Any] = data.get("properties", {})
    payload = _build_payload(data, keys=None, exclude_keys={"vehicle_id"})

    for vehicle in vehicle_ids:
        try:
            await api_instance.post_using_vehicle_property(vehicle, payload)
            await handle_entity(
                hass,
                data,
                call.service,
                api_instance.ucr_id,
                vehicle,
            )
        except HomeAssistantError as err:
            error_msg = await get_translation(
                hass,
                "exceptions",
                "api_post_using_vehicle_property_failed.message",
                {"vehicle_id": vehicle, "err": str(err)},
            )
            _LOGGER.error(error_msg)
            continue


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
    data = normalize_service_call_data(call.data)
    _validate_data(data, POST_USING_VEHICLE_CREW_VALIDATION_RULES)

    # get api instance
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # create payload
    # payload: dict[str, Any] = {}
    vehicle_ids: list[int] = data.get("vehicle_id")
    mode: str = data.get("mode", "")
    match mode:
        case "add":
            # payload = {"Crew": {"add": data.get("crew")}}
            payload = _build_payload(data, keys={"Crew": {"add": data.get("crew")}})

        case "remove":
            # payload = {"Crew": {"remove": data.get("crew")}}
            payload = _build_payload(data, keys={"Crew": {"remove": data.get("crew")}})

        case "reset":
            payload = {}

        case _:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_mode",
                translation_placeholders={"mode": mode},
            )

    for vehicle in vehicle_ids:
        try:
            await api_instance.post_using_vehicle_crew(vehicle, mode, payload)
            await handle_entity(hass, data, call.service, api_instance.ucr_id, vehicle)
        except HomeAssistantError as err:
            error_msg = await get_translation(
                hass,
                "exceptions",
                "api_post_using_vehicle_crew_failed.message",
                {"vehicle_id": vehicle, "err": str(err)},
            )
            _LOGGER.error(error_msg)
            continue


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
    data = normalize_service_call_data(call.data)
    _validate_data(data, POST_NEWS_VALIDATION_RULES)

    # get api instance
    api_instance = get_coordinator_key_from_device(hass, data.get("device_id"), "api")

    # create payload
    # payload: dict[str, Any] = {}
    notification_type: int = data.get("notification_type", 0)
    survey_flag = data.get("survey") or False

    news_data = {}
    survey_data = {}

    if survey_flag:
        survey_data = _extract_survey(data)
        news_data = _extract_news(data, notification_type)
    else:
        news_data = _extract_news(data, notification_type)

    # payload = {
    #     "News": news_data,
    #     "newssurvey": survey_data,
    # }
    payload = _build_payload(data, keys={"News": news_data, "newssurvey": survey_data})

    # call api function and handle entity
    title: str = data.get("title", "")
    try:
        await api_instance.post_news(payload)
        # no handle entity as new data needs to be fetched from Divera first
    except HomeAssistantError as err:
        error_msg = await get_translation(
            hass,
            "exceptions",
            "api_post_news_failed.message",
            {"title": title, "err": str(err)},
        )
        _LOGGER.error(error_msg)


def async_register_services(hass: HomeAssistant, domain: str) -> None:
    """Register services for DiveraControl.

    Args:
        hass: Home Assistant instance.
        domain: Domain name for services.
    """
    service_handlers: dict[str, Callable] = {
        "post_vehicle_status": handle_post_vehicle_status,
        "post_alarm": handle_post_alarm,
        "put_alarm": handle_put_alarm,
        "post_close_alarm": handle_post_close_alarm,
        "post_message": handle_post_message,
        "post_using_vehicle_property": handle_post_using_vehicle_property,
        "post_using_vehicle_crew": handle_post_using_vehicle_crew,
        "post_news": handle_post_news,
    }

    for service_name, handler in service_handlers.items():
        hass.services.async_register(
            domain,
            service_name,
            functools.partial(handler, hass),
        )
