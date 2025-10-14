"""Manage calendar for DiveraControl integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .calendar_entity import DiveraCalendar
from .const import D_UCR_ID


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up the Divera calendar entity."""
    calendar_entity = DiveraCalendar(
        config_entry.runtime_data,  # Coordinator
        config_entry.data[D_UCR_ID],
    )
    async_add_entities([calendar_entity])
