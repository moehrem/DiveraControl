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
    D_UPDATE_INTERVAL_DATA,
    D_UPDATE_INTERVAL_ALARM,
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
            update_interval=timedelta(seconds=hub[D_UPDATE_INTERVAL_DATA]),
            # update_interval_alarm=timedelta(seconds=hub[D_UPDATE_INTERVAL_ALARM]),
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
        self._last_data_update = now
        self._last_alarm_update = now

        self.interval_data = timedelta(seconds=hub[D_UPDATE_INTERVAL_DATA])
        self.interval_alarm = timedelta(seconds=hub[D_UPDATE_INTERVAL_ALARM])

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

            now = asyncio.get_running_loop().time()
            self._last_data_update = now

        except Exception as e:
            _LOGGER.error(
                "Error during initialization for HUB %s: %s", self.hub_id, str(e)
            )
        _LOGGER.debug("Finished initializing all data")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API and update cache on a regular basis."""
        now = asyncio.get_running_loop().time()

        # Wähle das richtige Intervall basierend auf der Alarmanzahl
        new_interval = (
            self.interval_alarm
            if self.data[D_ACTIVE_ALARM_COUNT] > 0
            else self.interval_data
        )

        # if needed, update coordinator interval
        if self.update_interval != new_interval:
            self.update_interval = new_interval
            _LOGGER.debug(
                "Update interval changed to %s seconds", new_interval.total_seconds()
            )

        # Helper function für eine Toleranz bei der Update-Ausführung
        def should_update(last_update, interval, tolerance=0.5):
            loop_time = now - last_update
            return (
                abs(loop_time - interval.total_seconds()) <= tolerance
                or loop_time > interval.total_seconds()
            )

        # Wähle den passenden Zeitstempel
        last_update = (
            self._last_alarm_update
            if self.data[D_ACTIVE_ALARM_COUNT] > 0
            else self._last_data_update
        )

        # Prüfe, ob ein Update nötig ist
        if should_update(last_update, new_interval):
            try:
                await update_operational_data(self.api, self.data)
                if self.data[D_ACTIVE_ALARM_COUNT] > 0:
                    self._last_alarm_update = now
                else:
                    self._last_data_update = now
                _LOGGER.debug("Finished updating operational data")

            except Exception as err:
                _LOGGER.error(
                    "Error fetching operational data for HUB %s: %s", self.hub_id, err
                )
                raise UpdateFailed(f"Error fetching data: {err}") from err

        return self.data

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
