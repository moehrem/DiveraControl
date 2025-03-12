"""Coordinator for myDivera integration."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DOMAIN,
    D_LAST_UPDATE_ALARM,
    D_LAST_UPDATE_DATA,
    # D_API_KEY,
    D_CLUSTER_NAME,
    # D_HUB_ID,
    D_UCR,
    D_UCR_ID,
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
    # D_ACCESS,
    # D_STATUS_CONF,
    # D_STATUS_SORT,
    D_VEHICLE,
    D_UPDATE_INTERVAL_DATA,
    D_UPDATE_INTERVAL_ALARM,
    D_OPEN_ALARMS,
)
from .data_updater import update_operational_data
from .utils import log_execution_time

LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, cluster, cluster_id):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=f"DiveraCoordinator_{cluster_id}",
            update_interval=timedelta(seconds=cluster[D_UPDATE_INTERVAL_DATA]),
        )
        self.api = api
        self.cluster_id = cluster_id
        self.ucr_id = cluster.get(D_UCR_ID, "")
        self.cluster_name = cluster.get(D_CLUSTER_NAME, "")
        self.cluster_data = {}
        self.admin_data = {}

        # **Listener for changes to ConfigEntry**
        async_dispatcher_connect(
            hass, f"{DOMAIN}_config_updated", self._config_entry_updated
        )

        now = asyncio.get_running_loop().time()
        self._last_data_update = now
        self._last_alarm_update = now

        self.interval_data = timedelta(seconds=cluster[D_UPDATE_INTERVAL_DATA])
        self.interval_alarm = timedelta(seconds=cluster[D_UPDATE_INTERVAL_ALARM])

        self._listeners = {}

    def init_cluster_data_structure(self):
        """Define main data structures for divera data and admin data."""
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
        self.admin_data = {
            D_UCR_ID: self.ucr_id,
            D_LAST_UPDATE_ALARM: "",
            D_LAST_UPDATE_DATA: "",
        }

    @log_execution_time
    async def init_cluster_data(self):
        """Initialize data at start one time only."""
        now = asyncio.get_running_loop().time()

        if not self.cluster_data or not self.admin_data:
            self.init_cluster_data_structure()

        try:
            changing_data = self.cluster_data
            changing_data = await update_operational_data(
                self.api, changing_data, self.admin_data
            )

            LOGGER.debug(
                "Successfully initialized data for unit '%s'",
                self.cluster_name,
            )

            # set last update times
            self.admin_data[D_LAST_UPDATE_ALARM] = now
            self.admin_data[D_LAST_UPDATE_DATA] = now

            self.cluster_data = changing_data

            LOGGER.info(
                "Successfully initialized data for unit '%s'", self.cluster_name
            )

        except Exception as e:
            LOGGER.error(
                "Error during initialization for HUB %s: %s",
                self.cluster_id,
                str(e),
            )

    @log_execution_time
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API and update cache on a regular basis."""
        now = asyncio.get_running_loop().time()
        open_alarms = self.cluster_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0)

        # Helper function für eine Toleranz bei der Update-Ausführung
        def should_update(last_update, interval, tolerance=0.5):
            loop_time = now - last_update
            return (
                abs(loop_time - interval.total_seconds()) <= tolerance
                or loop_time > interval.total_seconds()
            )

        # Wähle das richtige Intervall basierend auf der Alarmanzahl
        new_interval = self.interval_alarm if open_alarms > 0 else self.interval_data

        # Falls das Intervall geändert werden muss
        if self.update_interval != new_interval:
            self.update_interval = new_interval
            LOGGER.debug(
                "Update interval changed to %s seconds for unit '%s'",
                self.cluster_name,
            )

        # Wähle den passenden Zeitstempel
        last_update = (
            self.admin_data[D_LAST_UPDATE_ALARM]
            if open_alarms > 0
            else self.admin_data[D_LAST_UPDATE_DATA]
        )

        # Prüfe, ob ein Update nötig ist
        if should_update(last_update, new_interval):
            LOGGER.debug(
                "Start updating data for unit '%s'",
                self.cluster_name,
            )

            changing_data = await update_operational_data(
                self.api, self.cluster_data, self.admin_data
            )

            LOGGER.debug(
                "Successfully updated data for unit '%s' ",
                self.cluster_name,
            )

            # set update times
            if changing_data.get(D_ALARM, {}).get(D_OPEN_ALARMS, 0) > 0:
                changing_data[D_LAST_UPDATE_ALARM] = now
            else:
                changing_data[D_LAST_UPDATE_DATA] = now

        self.cluster_data = changing_data

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
                    LOGGER.debug("Error while removing listener: %s", e)

            self._listeners.pop(listener, None)

        LOGGER.debug("Removed update listeners for HUB: %s", self.cluster_id)

    async def _config_entry_updated(self, entry_id):
        """Load new data upon changes of configuration."""
        LOGGER.info(
            "Configuration for unit '%s' changed, reloading data",
            self.cluster_name,
        )
        # self.cluster_data.update(
        #     self.hass.config_entries.async_get_entry(entry_id).data.get(
        #         "user_cluster_relations", {}
        #     )
        # )
        # await self.initialize_data()

        # await self.async_request_refresh()

    # @log_execution_time
    # async def send_update_to_divera(self, entity_id, new_data, api_method: str):
    #     """Sendet eine Änderung von HA an Divera."""

    #     # Methode anhand des Strings aus self holen
    #     method = getattr(self, api_method, None)

    #     if method and callable(method):  # Prüfen, ob die Methode existiert
    #         success = await method(entity_id, new_data)
    #         if success:
    #             self.cluster_data["entities"][entity_id] = (
    #                 new_data  # Divera-Daten lokal anpassen
    #             )
    #     else:
    #         raise ValueError(
    #             f"API-Methode '{api_method}' existiert nicht oder ist nicht aufrufbar."
    #         )
