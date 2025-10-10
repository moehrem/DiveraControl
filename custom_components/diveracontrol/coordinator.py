"""Coordinator for myDivera integration."""

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
from .divera_api import DiveraAPI
from .divera_data import update_data
from .utils import log_execution_time, set_update_interval

_LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    """Manages all data handling."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: "DiveraAPI",
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

        self.cluster_name: str = config_entry.get(D_CLUSTER_NAME)
        self.ucr_id: str = config_entry.get(
            D_UCR_ID,
        )
        self.interval_alarm: timedelta = timedelta(
            seconds=config_entry.get(D_UPDATE_INTERVAL_ALARM)
        )
        self.interval_data: timedelta = timedelta(
            seconds=config_entry.get(D_UPDATE_INTERVAL_DATA)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"DiveraCoordinator_{self.ucr_id}",
            update_interval=self.interval_data,
        )

        self.api = api

        self._listeners = {}

        if not hasattr(self, "_listener_index"):
            self._listener_index = 0
        if not hasattr(self, "_removers"):
            self._removers: dict[int, Callable[[], None]] = {}

    def init_cluster_data_structure(self) -> None:
        """Define main data structures for divera data and admin data.

        Returns:
            None

        """

    @log_execution_time
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API."""

        # Initialisiere Struktur beim ersten Aufruf
        if not self.data:
            cluster_data: dict[str, Any] = {
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
        else:
            cluster_data = self.data

        try:
            intervall_data = {
                D_UPDATE_INTERVAL_ALARM: self.interval_alarm,
                D_UPDATE_INTERVAL_DATA: self.interval_data,
            }

            await update_data(self.api, cluster_data)

            # dynamically change update interval
            self.update_interval = set_update_interval(
                cluster_data, intervall_data, self.update_interval
            )

            _LOGGER.debug(
                "Successfully updated data for unit '%s'",
                self.cluster_name,
            )

            return cluster_data

        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    def async_add_listener(
        self,
        update_callback: Callable,
        context: Any = None,
    ) -> Callable:
        """Add a listener and store the remove function.

        Args:
            update_callback (callable): Callback function to be called when data is updated.
            context (Any): optional context for the listener.

        Returns:
            callable: function to remove listener.

        """
        remove_listener = super().async_add_listener(update_callback)

        self._listener_index += 1
        listener_id = self._listener_index

        self._listeners[listener_id] = (update_callback, context)
        self._removers[listener_id] = remove_listener

        return remove_listener

    async def remove_listeners(self) -> None:
        """Remove all update listeners for this coordinator.

        Returns:
            None

        """

        remover_ids = list(self._removers.keys())

        for listener_id in remover_ids:
            remove_func = self._removers.get(listener_id)

            if callable(remove_func):
                try:
                    remove_func()
                except Exception as e:
                    _LOGGER.debug("Error while removing listener: %s", e)

            self._listeners.pop(listener_id, None)
            self._removers.pop(listener_id, None)

        _LOGGER.debug("Removed update listeners for HUB: %s", self.ucr_id)
