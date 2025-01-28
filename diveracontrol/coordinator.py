"""Coordinator for myDivera integration."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    D_ACTIVE_ALARM_COUNT,
    D_HUB_ID,
    D_UCR,
    D_UCR_DEFAULT,
    D_UCR_ACTIVE,
    D_TS,
    D_USER,
    D_STATUS,
    D_CLUSTER,
    D_MONITOR,
    D_ALARM,
    D_NEWS,
    D_EVENTS,
    D_DM,
    D_MESSAGE_CHANNEL,
    D_MESSAGE,
    D_LOCALMONITOR,
    D_STATUSPLAN,
    D_ACCESS,
    D_STATUS_CONF,
    D_STATUS_SORT,
    D_CLUSTER_ADDRESS,
    D_VEHICLE,
)
from .data_updater import update_operational_data

_LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, hub, hub_id, entry_id=None):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"DiveraCoordinator_{hub_id}",
            update_interval=timedelta(seconds=hub["update_interval_alarms"]),
        )
        self.api = api
        self.hub_id = hub_id
        self.entry_id = entry_id

        self.data = {
            D_HUB_ID: hub_id,
            D_ACTIVE_ALARM_COUNT: "",
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
            D_ACCESS: {},
            D_STATUS_CONF: {},
            D_STATUS_SORT: {},
            D_CLUSTER_ADDRESS: {},
            D_VEHICLE: {},
        }

        now = asyncio.get_running_loop().time()
        self._last_masterdata_update = now
        self._last_alarm_update = now

        self.interval_ops = timedelta(seconds=hub["update_interval_alarms"])

        self._listeners = {}

    async def initialize_data(self):
        """Initialize data at start one single time only."""
        try:
            await update_operational_data(self.api, self.data)

            unit_name = (
                self.data.get(D_UCR, {}).get(self.hub_id, "").get("name", "Unknown")
            )
            _LOGGER.info(
                "Successfully initialized data for HUB %s (%s) ", unit_name, self.hub_id
            )

        except Exception as e:
            _LOGGER.error(
                "Error during initialization for HUB %s: %s", self.hub_id, str(e)
            )
        _LOGGER.debug("Finished initializing all data")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API and update cache on a regular basis."""
        now = asyncio.get_running_loop().time()

        # Helper function to handle loop time tolerances
        def should_update(loop_time, interval, tolerance=0.5):
            return abs(loop_time - interval) <= tolerance or loop_time > interval

        # Update operational data
        try:
            loop_time_ops = now - self._last_alarm_update
            _LOGGER.debug("Ops data looptime = %s", loop_time_ops)
            if should_update(loop_time_ops, self.interval_ops.total_seconds()):
                self._last_alarm_update = now
                await update_operational_data(self.api, self.data)
                _LOGGER.debug("Finished updating operational data")

        except Exception as err:
            _LOGGER.error(
                "Error fetching operational data for HUB %s: %s", self.hub_id, err
            )
            raise UpdateFailed(f"Error fetching data: {err}") from err

        return {
            D_HUB_ID: self.data[D_HUB_ID],
            D_ACTIVE_ALARM_COUNT: self.data[D_ACTIVE_ALARM_COUNT],
            D_UCR: self.data[D_UCR],
            D_UCR_DEFAULT: self.data[D_UCR_DEFAULT],
            D_UCR_ACTIVE: self.data[D_UCR_ACTIVE],
            D_TS: self.data[D_TS],
            D_USER: self.data[D_USER],
            D_STATUS: self.data[D_STATUS],
            D_CLUSTER: self.data[D_CLUSTER],
            D_MONITOR: self.data[D_MONITOR],
            D_ALARM: self.data[D_ALARM],
            D_NEWS: self.data[D_NEWS],
            D_EVENTS: self.data[D_EVENTS],
            D_DM: self.data[D_DM],
            D_MESSAGE_CHANNEL: self.data[D_MESSAGE_CHANNEL],
            D_MESSAGE: self.data[D_MESSAGE],
            D_LOCALMONITOR: self.data[D_LOCALMONITOR],
            D_STATUSPLAN: self.data[D_STATUSPLAN],
            D_ACCESS: self.data[D_ACCESS],
            D_STATUS_CONF: self.data[D_STATUS_CONF],
            D_STATUS_SORT: self.data[D_STATUS_SORT],
            D_CLUSTER_ADDRESS: self.data[D_CLUSTER_ADDRESS],
            D_VEHICLE: self.data[D_VEHICLE],
        }

    def async_add_listener(self, update_callback):
        """Add a listener and store the remove function."""
        remove_listener = super().async_add_listener(update_callback)
        self._listeners[remove_listener] = (update_callback, None)
        return remove_listener

    async def remove_listeners(self) -> None:
        """Remove all update listeners for this coordinator."""
        for remove_listener in list(self._listeners.keys()):
            remove_listener()  # Remove the listener
            self._listeners.pop(remove_listener, None)  # Remove it from the dictionary
        _LOGGER.info("Removed update listeners for HUB: %s", self.hub_id)
