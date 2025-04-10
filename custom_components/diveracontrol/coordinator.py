"""Coordinator for myDivera integration."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    D_CLUSTER_NAME,
    D_UCR,
    D_CLUSTER_ID,
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
    D_UPDATE_INTERVAL_DATA,
    D_UPDATE_INTERVAL_ALARM,
    D_OPEN_ALARMS,
)
from .data_updater import update_data
from .utils import log_execution_time, set_update_interval

_LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    """Manages all data handling."""

    def __init__(self, hass: HomeAssistant, api, config_entry, cluster_id) -> None:
        """Initialize DiveraControl coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"DiveraCoordinator_{cluster_id}",
        )
        self.api = api
        # self.cluster_id = cluster_id
        # self.cluster_name = config_entry.get(D_CLUSTER_NAME, "")
        self.cluster_data = {}
        self.admin_data = {
            D_CLUSTER_NAME: config_entry.get(D_CLUSTER_NAME, "Unknown"),
            D_CLUSTER_ID: cluster_id,
            D_UPDATE_INTERVAL_ALARM: timedelta(
                seconds=config_entry[D_UPDATE_INTERVAL_ALARM]
            ),
            D_UPDATE_INTERVAL_DATA: timedelta(
                seconds=config_entry[D_UPDATE_INTERVAL_DATA]
            ),
        }

        # self._interval_data = timedelta(seconds=config_entry[D_UPDATE_INTERVAL_DATA])
        # self._interval_alarm = timedelta(seconds=config_entry[D_UPDATE_INTERVAL_ALARM])

        self._listeners = {}

    def init_cluster_data_structure(self) -> None:
        """Define main data structures for divera data and admin data."""
        if not self.cluster_data:
            self.cluster_data = {
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
            }

        if not self.admin_data:
            self.admin_data = {
                D_CLUSTER_NAME: "Unknown",
                D_CLUSTER_ID: "Unknown",
                D_UPDATE_INTERVAL_ALARM: 0,
                D_UPDATE_INTERVAL_DATA: 0,
            }

    @log_execution_time
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API and update cache on a regular basis.

        Returns:
            self.cluster_data (dict): all new data, freshly requested from Divera.

        """
        if not self.cluster_data or not self.admin_data:
            self.init_cluster_data_structure()

        try:
            await update_data(self.api, self.cluster_data, self.admin_data)

            self.update_interval = set_update_interval(
                self.update_interval,
                self.cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0),
                self.admin_data,
            )

            _LOGGER.debug(
                "Successfully updated data for unit '%s' ",
                self.admin_data[D_CLUSTER_NAME],
            )

        except Exception as err:
            self.async_set_update_error(err)

        # update entities
        self.async_set_updated_data(self.cluster_data)

        return self.cluster_data

    def async_add_listener(self, update_callback):
        """Add a listener and store the remove function."""
        remove_listener = super().async_add_listener(update_callback)
        self._listeners[remove_listener] = (update_callback, None)
        return remove_listener

    async def remove_listeners(self) -> None:
        """Remove all update listeners for this coordinator."""
        to_remove = list(self._listeners.keys())

        for listener in to_remove:
            if callable(listener):
                try:
                    listener()
                except Exception as e:
                    _LOGGER.debug("Error while removing listener: %s", e)

            self._listeners.pop(listener, None)

        _LOGGER.debug(
            "Removed update listeners for HUB: %s", self.admin_data[D_CLUSTER_ID]
        )
