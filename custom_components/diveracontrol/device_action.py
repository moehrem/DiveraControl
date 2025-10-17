"""Device actions for DiveraControl."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import device_registry as dr, selector
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
)

from .const import (
    D_UCR_ID,
    DOMAIN,
    PERM_ALARM,
    PERM_MANAGEMENT,
    PERM_MESSAGES,
    PERM_NEWS,
    PERM_STATUS_VEHICLE,
)
from .utils import get_coordinator_key_from_device, get_translation, permission_check

ACTION_TYPES: tuple[str, ...] = (
    "post_vehicle_status",
    "post_alarm",
    "put_alarm",
    "post_close_alarm",
    "post_message",
    "post_using_vehicle_property",
    "post_using_vehicle_crew",
    "post_news",
)

ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("domain"): DOMAIN,
        vol.Required("type"): vol.In(ACTION_TYPES),
    },
    extra=vol.ALLOW_EXTRA,
)


async def _get_selector_options(
    hass: HomeAssistant,
    device_id: str,
    data_path: str,
    label_format: str | None = "",
) -> Sequence[SelectOptionDict]:
    """Generic function to get selector options from coordinator data.

    Args:
        hass: Home Assistant instance
        device_id: Device ID to get data for
        data_path: Dot-notation path to data (e.g., "cluster.vehicle")
        label_format: Format string for label (e.g., "{name} / {shortname}")
                     If None, uses {name}

    Returns:
        List of option dictionaries with value and label
    """
    # Check for static options first (don't require coordinator data)
    if data_path == "notification_type_options":
        # Special case for static options
        return [
            {
                "value": "1",
                "label": await get_translation(
                    hass, "selector", "notification_type_options.options.1"
                ),
            },
            {
                "value": "2",
                "label": await get_translation(
                    hass, "selector", "notification_type_options.options.2"
                ),
            },
            {
                "value": "3",
                "label": await get_translation(
                    hass, "selector", "notification_type_options.options.3"
                ),
            },
            {
                "value": "4",
                "label": await get_translation(
                    hass, "selector", "notification_type_options.options.4"
                ),
            },
        ]

    if data_path == "mode_options":
        return [
            {
                "value": "add",
                "label": await get_translation(
                    hass, "selector", "mode_options.options.add"
                ),
            },
            {
                "value": "remove",
                "label": await get_translation(
                    hass, "selector", "mode_options.options.remove"
                ),
            },
            {
                "value": "reset",
                "label": await get_translation(
                    hass, "selector", "mode_options.options.reset"
                ),
            },
        ]

    if data_path in [
        "newssurvey_show_result_count_options",
        "newssurvey_show_result_names_options",
    ]:
        return [
            {
                "value": "0",
                "label": await get_translation(
                    hass, "selector", "newssurvey_result_options.options.0"
                ),
            },
            {
                "value": "1",
                "label": await get_translation(
                    hass, "selector", "newssurvey_result_options.options.1"
                ),
            },
            {
                "value": "2",
                "label": await get_translation(
                    hass, "selector", "newssurvey_result_options.options.2"
                ),
            },
        ]

    # For dynamic options, get coordinator data
    coor_data: dict[str, Any] = get_coordinator_key_from_device(hass, device_id, "data")

    if not device_id:
        return []

    # Navigate data path
    for key in data_path.split("."):
        coor_data = coor_data.get(key, {})
        if not coor_data:
            return []

    # Handle items wrapper if present
    if "items" in coor_data:
        coor_data = coor_data["items"]

    if not coor_data:
        return []

    if label_format is None:
        label_format = "{name}"

    return [
        {
            "value": str(item_id),
            "label": label_format.format(**item),
        }
        for item_id, item in coor_data.items()
    ]


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List available actions for a DiveraControl device."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device or not device.config_entries:
        return []

    action_types: list[str] = []

    # check action type permissions
    entry_id = next(iter(device.config_entries))
    config_entry = hass.config_entries.async_get_entry(entry_id)
    if not config_entry:
        return []

    ucr_id: str | None = config_entry.data.get(D_UCR_ID)
    if not ucr_id:
        return []

    if permission_check(hass, ucr_id, PERM_MANAGEMENT):
        action_types = [
            "post_vehicle_status",
            "post_alarm",
            "put_alarm",
            "post_close_alarm",
            "post_message",
            "post_using_vehicle_property",
            "post_using_vehicle_crew",
            "post_news",
        ]

    else:
        if permission_check(hass, ucr_id, PERM_STATUS_VEHICLE):
            action_types.extend(
                [
                    "post_vehicle_status",
                    "post_using_vehicle_property",
                    "post_using_vehicle_crew",
                ]
            )
        if permission_check(hass, ucr_id, PERM_ALARM):
            action_types.extend(["post_alarm", "put_alarm", "post_close_alarm"])
        if permission_check(hass, ucr_id, PERM_MESSAGES):
            action_types.append("post_message")
        if permission_check(hass, ucr_id, PERM_NEWS):
            action_types.append("post_news")

    return [
        {"domain": DOMAIN, "type": action_type, "device_id": device_id}
        for action_type in action_types
    ]


async def async_call_action_from_config(
    hass: HomeAssistant,
    config: dict[str, Any],
    variables: dict[str, Any],
    context: Context | None,
) -> None:
    """Execute a device action."""
    validated_config: dict[Any, Any] = {}
    try:
        validated_config = ACTION_SCHEMA(config)
    except vol.Invalid as err:
        raise InvalidDeviceAutomationConfig(err) from err

    service_data = {
        "device_id": validated_config["device_id"],
        **{
            key: value
            for key, value in validated_config.items()
            if key not in ["domain", "type", "device_id", "data"]
        },
    }

    # optional: add data dict if available
    if data := validated_config.get("data"):
        service_data.update(data)

    await hass.services.async_call(
        DOMAIN,
        validated_config["type"],
        service_data,
        blocking=True,
        context=context,
    )


async def async_validate_action_config(
    hass: HomeAssistant, config: dict[str, Any]
) -> dict[str, Any]:
    """Validate action config."""
    return ACTION_SCHEMA(config)


async def async_get_action_capabilities(
    hass: HomeAssistant, config: dict[str, Any]
) -> dict[str, vol.Schema]:
    """Return extra fields for the action."""
    action_type: str | None = config.get("type")
    device_id: str | None = config.get("device_id")

    if action_type is None or device_id is None:
        return {}

    if action_type == "post_vehicle_status":
        vehicle_options = await _get_selector_options(
            hass, device_id, "cluster.vehicle", "{name} / {shortname}"
        )
        fms_status_options = await _get_selector_options(
            hass, device_id, "cluster.fms_status.items", "{number} - {name}"
        )

        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required("vehicle"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=vehicle_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if vehicle_options
                    else vol.Coerce(int),
                    vol.Optional("status"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=fms_status_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if fms_status_options
                    else vol.Coerce(int),
                    vol.Optional("status_id"): NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=10,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional("status_note"): str,
                    vol.Optional("lat"): NumberSelector(
                        NumberSelectorConfig(
                            min=-90.0,
                            max=90.0,
                            step="any",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional("lng"): NumberSelector(
                        NumberSelectorConfig(
                            min=-180.0,
                            max=180.0,
                            step="any",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                }
            )
        }

    if action_type in ["post_alarm", "put_alarm"]:
        notification_type_options = await _get_selector_options(
            hass, device_id, "notification_type_options"
        )
        vehicle_options = await _get_selector_options(
            hass, device_id, "cluster.vehicle", "{name} / {shortname}"
        )
        user_cluster_relation_options = await _get_selector_options(
            hass, device_id, "cluster.consumer", "{firstname} {lastname}"
        )
        group_options = await _get_selector_options(
            hass, device_id, "cluster.group", "{name}"
        )
        user_status_options = await _get_selector_options(
            hass, device_id, "cluster.status", "{name}"
        )
        alarmcode_options = await _get_selector_options(
            hass, device_id, "cluster.alarmcode", "{name}"
        )
        alarm_options = await _get_selector_options(
            hass, device_id, "alarm.items", "{title} ({id})"
        )

        alarm_selector: dict[Any, Any] = (
            {
                vol.Required("alarm_id"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=alarm_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                if alarm_options
                else vol.Coerce(int)
            }
            if action_type == "put_alarm"
            else {}
        )

        return {
            "extra_fields": vol.Schema(
                {
                    **alarm_selector,
                    vol.Required("title"): str,
                    vol.Required("notification_type"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=notification_type_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional("alarmcode_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=alarmcode_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if alarmcode_options
                    else str,  # fallback: list of commeseparated string
                    vol.Optional("foreign_id"): str,
                    vol.Optional("group"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=group_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if group_options
                    else str,  # Comma-separated list
                    vol.Optional("user_cluster_relation"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=user_cluster_relation_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if user_cluster_relation_options
                    else str,  # Comma-separated list als Fallback
                    vol.Optional("notification_filter_vehicle"): bool,
                    vol.Optional("vehicle"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=vehicle_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if vehicle_options
                    else str,  # Comma-separated list
                    vol.Optional("notification_filter_status"): bool,
                    vol.Optional("status"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=user_status_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if user_status_options
                    else str,  # Comma-separated list
                    vol.Optional("priority"): bool,
                    vol.Optional("text"): str,
                    vol.Optional("address"): str,
                    vol.Optional("lat"): NumberSelector(
                        NumberSelectorConfig(
                            min=-90.0,
                            max=90.0,
                            step="any",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional("lng"): NumberSelector(
                        NumberSelectorConfig(
                            min=-180.0,
                            max=180.0,
                            step="any",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional("scene_object"): str,
                    vol.Optional("caller"): str,
                    vol.Optional("patient"): str,
                    vol.Optional("units"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=vehicle_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    ),
                    vol.Optional("destination"): bool,
                    vol.Optional("destination_address"): str,
                    vol.Optional("destination_lat"): NumberSelector(
                        NumberSelectorConfig(
                            min=-90.0,
                            max=90.0,
                            step="any",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional("destination_lng"): NumberSelector(
                        NumberSelectorConfig(
                            min=-180.0,
                            max=180.0,
                            step="any",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional("remarks"): str,
                    vol.Optional("response_time"): vol.Coerce(int),
                    vol.Optional("send_push"): bool,
                    vol.Optional("send_sms"): bool,
                    vol.Optional("send_call"): bool,
                    vol.Optional("send_mail"): bool,
                    vol.Optional("send_pager"): bool,
                    vol.Optional("closed"): bool,
                    vol.Optional("message_channel"): bool,
                    vol.Optional("notification_filter_access"): bool,
                    vol.Optional("ts_publish"): selector.DateTimeSelector(),
                    vol.Optional("ts_close"): selector.DateTimeSelector(),
                }
            )
        }

    if action_type == "post_close_alarm":
        alarm_options = await _get_selector_options(
            hass, device_id, "alarm.items", "{title} ({id})"
        )

        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required("alarm_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=alarm_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if alarm_options
                    else vol.Coerce(int),
                    vol.Optional("closed"): bool,
                    vol.Optional("report"): str,
                }
            )
        }

    if action_type == "post_message":
        alarm_options = await _get_selector_options(
            hass, device_id, "alarm.items", "{title} ({id})"
        )
        message_channel_options = await _get_selector_options(
            hass, device_id, "message_channel.items", "{title} ({id})"
        )

        return {
            "extra_fields": vol.Schema(
                {
                    vol.Optional("message_channel_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=message_channel_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if message_channel_options
                    else vol.Coerce(int),
                    vol.Optional("alarm_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=alarm_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if alarm_options
                    else vol.Coerce(int),
                    vol.Optional("text"): str,
                }
            )
        }

    if action_type == "post_using_vehicle_property":
        vehicle_options = await _get_selector_options(
            hass, device_id, "cluster.vehicle", "{name} / {shortname}"
        )

        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required("vehicle"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=vehicle_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if vehicle_options
                    else str,
                    vol.Optional("properties"): selector.ObjectSelector(),
                }
            )
        }

    if action_type == "post_using_vehicle_crew":
        vehicle_options = await _get_selector_options(
            hass, device_id, "cluster.vehicle", "{name} / {shortname}"
        )
        crew_options = await _get_selector_options(
            hass, device_id, "cluster.consumer", "{firstname} {lastname}"
        )
        mode_options = await _get_selector_options(
            hass, device_id, "mode_options", "{DUMMY}"
        )

        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required("vehicle"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=vehicle_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if vehicle_options
                    else str,  # Comma-separated list
                    vol.Required("mode"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=mode_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional("crew"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=crew_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if crew_options
                    else str,  # Comma-separated list of user IDs
                }
            )
        }

    if action_type == "post_news":
        notification_type_options = await _get_selector_options(
            hass, device_id, "notification_type_options"
        )
        group_options = await _get_selector_options(
            hass, device_id, "cluster.group", "{name}"
        )
        user_cluster_relation_options = await _get_selector_options(
            hass, device_id, "cluster.consumer", "{firstname} {lastname}"
        )
        newssurvey_show_result_count_options = await _get_selector_options(
            hass, device_id, "newssurvey_show_result_count_options"
        )
        newssurvey_show_result_names_options = await _get_selector_options(
            hass, device_id, "newssurvey_show_result_names_options"
        )

        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required("title"): str,
                    vol.Required("notification_type"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=notification_type_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional("user_cluster_relation"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=user_cluster_relation_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if user_cluster_relation_options
                    else str,  # Comma-separated list als Fallback
                    vol.Optional("group"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=group_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            multiple=True,
                        )
                    )
                    if group_options
                    else str,  # Comma-separated list
                    vol.Optional("text"): str,
                    vol.Optional("address"): str,
                    vol.Optional("survey"): bool,
                    vol.Optional("private_mode"): bool,
                    vol.Optional("send_push"): bool,
                    vol.Optional("send_sms"): bool,
                    vol.Optional("send_call"): bool,
                    vol.Optional("send_mail"): bool,
                    vol.Optional("send_pager"): bool,
                    vol.Optional("archive"): bool,
                    vol.Optional("ts_archive"): selector.DateTimeSelector(),
                    # survey-specific fields
                    vol.Optional("newssurvey_title"): str,
                    vol.Optional(
                        "newssurvey_show_result_count"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=newssurvey_show_result_count_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if newssurvey_show_result_count_options
                    else vol.Coerce(int),
                    vol.Optional(
                        "newssurvey_show_result_names"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=newssurvey_show_result_names_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                    if newssurvey_show_result_names_options
                    else vol.Coerce(int),
                    vol.Optional("newssurvey_multiple_answers"): bool,
                    vol.Optional("newssurvey_custom_answers"): bool,
                    vol.Optional("newssurvey_response_until"): bool,
                    vol.Optional("newssurvey_ts_response"): selector.DateTimeSelector(),
                    vol.Optional("newssurvey_answers"): selector.ObjectSelector(),
                    vol.Optional("newssurvey_sorting"): selector.ObjectSelector(),
                }
            )
        }

    # Fallback für Actions ohne spezifische Felder
    return {}
