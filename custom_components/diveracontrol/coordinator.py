"""Coordinator for myDivera integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import DiveraAPI
from .const import (
    D_ALARM,
    D_CLUSTER,
    D_CLUSTER_NAME,
    D_DM,
    D_EVENTS,
    D_LOCALMONITOR,
    D_MESSAGE,
    D_MESSAGE_CHANNEL,
    D_MONITOR,
    D_NEWS,
    D_OPEN_ALARMS,
    D_STATUS,
    D_STATUSPLAN,
    D_TS,
    D_UCR,
    D_UCR_ACTIVE,
    D_UCR_DEFAULT,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USER,
)
from .data_updater import update_data
from .utils import log_execution_time, set_update_interval

_LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    """Manages all data handling."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DiveraAPI,
        config_entry: dict,
    ) -> None:
        """Initialize DiveraControl coordinator.

        Args:
            hass (HomeAssistant): Home Assistant instance.
            api (DiveraAPI): Divera API instance.
            config_entry (dict): Configuration entry for the integration.

        Returns:
            None

        """

        super().__init__(
            hass,
            _LOGGER,
            name=f"DiveraCoordinator_{config_entry.get(D_UCR_ID)}",
        )
        self.api = api
        self.cluster_data = {}
        self.admin_data = {
            D_CLUSTER_NAME: config_entry.get(D_CLUSTER_NAME, "Unknown"),
            D_UCR_ID: config_entry.get(D_UCR_ID),
            D_UPDATE_INTERVAL_ALARM: timedelta(
                seconds=config_entry[D_UPDATE_INTERVAL_ALARM]
            ),
            D_UPDATE_INTERVAL_DATA: timedelta(
                seconds=config_entry[D_UPDATE_INTERVAL_DATA]
            ),
        }

        self._listeners = {}

    def init_cluster_data_structure(self) -> None:
        """Define main data structures for divera data and admin data.

        Returns:
            None

        """
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
                D_UCR_ID: "Unknown",
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

    def async_add_listener(self, update_callback: callable) -> callable:
        """Add a listener and store the remove function.

        Args:
            update_callback (callable): Callback function to be called when data is updated.

        Returns:
            callable: function to remove listener.

        """
        remove_listener = super().async_add_listener(update_callback)
        self._listeners[remove_listener] = (update_callback, None)
        return remove_listener

    async def remove_listeners(self) -> None:
        """Remove all update listeners for this coordinator.

        Returns:
            None

        """
        to_remove = list(self._listeners.keys())

        for listener in to_remove:
            if callable(listener):
                try:
                    listener()
                except Exception as e:
                    _LOGGER.debug("Error while removing listener: %s", e)

            self._listeners.pop(listener, None)

        _LOGGER.debug("Removed update listeners for HUB: %s", self.admin_data[D_UCR_ID])
