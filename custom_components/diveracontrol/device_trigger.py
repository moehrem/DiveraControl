"""Device triggers for DiveraControl."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import (
    numeric_state as numeric_state_trigger,
)
from homeassistant.const import (
    CONF_ABOVE,
    CONF_BELOW,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

TRIGGER_TYPE_NEW_ALARM = "new_alarm"
TRIGGER_TYPE_ALL_ALARMS_CLOSED = "all_alarms_closed"

TRIGGER_TYPES = {TRIGGER_TYPE_NEW_ALARM, TRIGGER_TYPE_ALL_ALARMS_CLOSED}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id_or_uuid,
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

    entity_entry = entries[0]

    base_trigger = {
        CONF_PLATFORM: "device",
        CONF_DOMAIN: DOMAIN,
        CONF_DEVICE_ID: device_id,
        CONF_ENTITY_ID: entity_entry.id,
    }

    return [
        {**base_trigger, CONF_TYPE: TRIGGER_TYPE_NEW_ALARM},
        {**base_trigger, CONF_TYPE: TRIGGER_TYPE_ALL_ALARMS_CLOSED},
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    trigger_type = config[CONF_TYPE]

    if (
        trigger_type == TRIGGER_TYPE_NEW_ALARM
    ):  # TRIGGER_TYPE_NEW_ALARM to fire when the number of open alarms raises
        numeric_state_config = {
            CONF_PLATFORM: "numeric_state",
            CONF_ENTITY_ID: config[CONF_ENTITY_ID],
            CONF_ABOVE: 0,
            "from": "any",
        }
    else:  # TRIGGER_TYPE_ALL_ALARMS_CLOSED
        numeric_state_config = {
            CONF_PLATFORM: "numeric_state",
            CONF_ENTITY_ID: config[CONF_ENTITY_ID],
            CONF_BELOW: 1,
        }

    numeric_state_config = await numeric_state_trigger.async_validate_trigger_config(
        hass, numeric_state_config
    )
    return await numeric_state_trigger.async_attach_trigger(
        hass, numeric_state_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities."""
    return {}
