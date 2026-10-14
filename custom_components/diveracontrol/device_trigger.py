"""Device triggers for DiveraControl."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    ALARM_EVENT_TYPE,
    ATTR_ALARM_EVENT_TYPE,
    DOMAIN,
    TRIGGER_ALARM_CLOSED,
    TRIGGER_ALARM_OPENED,
    TRIGGER_ALARM_UPDATED,
)

TRIGGER_TYPE_NEW_ALARM = "new_alarm"
TRIGGER_TYPE_ALL_ALARMS_CLOSED = "all_alarms_closed"

TRIGGER_TYPE_ALARM_OPENED = TRIGGER_ALARM_OPENED
TRIGGER_TYPE_ALARM_UPDATED = TRIGGER_ALARM_UPDATED
TRIGGER_TYPE_ALARM_CLOSED = TRIGGER_ALARM_CLOSED

LIFECYCLE_TRIGGER_TYPES = {
    TRIGGER_TYPE_ALARM_OPENED,
    TRIGGER_TYPE_ALARM_UPDATED,
    TRIGGER_TYPE_ALARM_CLOSED,
}

TRIGGER_TYPES = {
    TRIGGER_TYPE_NEW_ALARM,
    TRIGGER_TYPE_ALL_ALARMS_CLOSED,
} | LIFECYCLE_TRIGGER_TYPES

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """Return a list of triggers for the given device."""
    entity_registry = er.async_get(hass)

    entries = [
        entry
        for entry in er.async_entries_for_device(entity_registry, device_id)
        if entry.domain == "sensor"
        and entry.unique_id is not None
        and entry.unique_id.endswith("_open_alarms")
    ]

    if not entries:
        return []

    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: trigger_type,
        }
        for trigger_type in TRIGGER_TYPES
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    trigger_type = config[CONF_TYPE]

    event_data = {CONF_DEVICE_ID: config[CONF_DEVICE_ID]}
    if trigger_type in (
        LIFECYCLE_TRIGGER_TYPES
        | {TRIGGER_TYPE_NEW_ALARM, TRIGGER_TYPE_ALL_ALARMS_CLOSED}
    ):
        event_data[ATTR_ALARM_EVENT_TYPE] = trigger_type.removeprefix("alarm_")

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: ALARM_EVENT_TYPE,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities."""
    return {}
