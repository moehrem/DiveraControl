"""Coordinator for myDivera integration."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DOMAIN,
    D_ACTIVE_ALARM_COUNT,
    D_LAST_UPDATE_ALARM,
    D_LAST_UPDATE_DATA,
    D_API_KEY,
    D_HUB_ID,
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
    D_ACCESS,
    D_STATUS_CONF,
    D_STATUS_SORT,
    D_CLUSTER_ADDRESS,
    D_VEHICLE,
    D_UPDATE_INTERVAL_DATA,
    D_UPDATE_INTERVAL_ALARM,
    D_CLUSTER_ID,
)
from .data_updater import update_operational_data
from .utils import log_execution_time

LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, cluster, cluster_id, entry_id=None):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=f"DiveraCoordinator_{cluster_id}",
            update_interval=timedelta(seconds=cluster[D_UPDATE_INTERVAL_DATA]),
            # update_interval_alarm=timedelta(seconds=hub[D_UPDATE_INTERVAL_ALARM]),
        )
        self.api = api
        self.cluster_id = cluster_id
        self.cluster_name = cluster.get("name", "")
        # self.entry_id = entry_id
        self.cluster_data = {}

        # **Listener für Änderungen im ConfigEntry**
        async_dispatcher_connect(
            hass, f"{DOMAIN}_config_updated", self._config_entry_updated
        )

        for ucr_id in cluster.get("user_cluster_relations", {}):
            self.cluster_data[ucr_id] = {
                D_UCR_ID: ucr_id,
                D_API_KEY: cluster.get("user_cluster_relations", {})
                .get(ucr_id, "")
                .get(D_API_KEY, ""),
                D_ACTIVE_ALARM_COUNT: "",
                D_LAST_UPDATE_ALARM: "",
                D_LAST_UPDATE_DATA: "",
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

        self.interval_data = timedelta(seconds=cluster[D_UPDATE_INTERVAL_DATA])
        self.interval_alarm = timedelta(seconds=cluster[D_UPDATE_INTERVAL_ALARM])

        self._listeners = {}

    @log_execution_time
    async def initialize_data(self):
        """Initialize data at start one time only."""
        now = asyncio.get_running_loop().time()

        for ucr_id, ucr_data in self.cluster_data.items():
            try:
                ucr_data = {
                    D_UCR_ID: ucr_id,
                    D_API_KEY: ucr_data.get(D_API_KEY, ""),
                    D_ACTIVE_ALARM_COUNT: "",
                    D_LAST_UPDATE_ALARM: "",
                    D_LAST_UPDATE_DATA: "",
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

                ucr_data = await update_operational_data(self.api, ucr_data)

                user_name = f"{ucr_data.get(D_USER, {}).get('firstname', '')} {ucr_data.get(D_USER, {}).get('lastname', '')}"
                LOGGER.debug(
                    "Successfully initialized data for user %s (%s) ",
                    user_name,
                    ucr_id,
                )

                # set last update times
                ucr_data[D_LAST_UPDATE_ALARM] = now
                ucr_data[D_LAST_UPDATE_DATA] = now

            except Exception as e:
                LOGGER.error(
                    "Error during initialization for HUB %s: %s",
                    self.cluster_id,
                    str(e),
                )

            self.cluster_data[ucr_id] = ucr_data

        LOGGER.info("Successfully initialized data for unit %s", self.cluster_name)

    @log_execution_time
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API and update cache on a regular basis."""
        now = asyncio.get_running_loop().time()

        # Helper function für eine Toleranz bei der Update-Ausführung
        def should_update(last_update, interval, tolerance=0.5):
            loop_time = now - last_update
            return (
                abs(loop_time - interval.total_seconds()) <= tolerance
                or loop_time > interval.total_seconds()
            )

        for ucr_id, ucr_data in self.cluster_data.items():
            # Wähle das richtige Intervall basierend auf der Alarmanzahl
            new_interval = (
                self.interval_alarm
                if ucr_data.get(D_ACTIVE_ALARM_COUNT, 0) > 0
                else self.interval_data
            )

            # Falls das Intervall geändert werden muss
            if self.update_interval != new_interval:
                self.update_interval = new_interval
                LOGGER.debug(
                    "Update interval changed to %s seconds for UCR %s",
                    new_interval.total_seconds(),
                    ucr_id,
                )

            # Wähle den passenden Zeitstempel
            last_update = (
                ucr_data[D_LAST_UPDATE_ALARM]
                if ucr_data.get(D_ACTIVE_ALARM_COUNT, 0) > 0
                else ucr_data[D_LAST_UPDATE_DATA]
            )

            # Prüfe, ob ein Update nötig ist
            if should_update(last_update, new_interval):
                user_name = f"{ucr_data.get(D_USER, {}).get('firstname', '')} {ucr_data.get(D_USER, {}).get('lastname', '')}"

                LOGGER.debug(
                    "Start updating data for user %s (%s) ",
                    user_name,
                    ucr_id,
                )

                ucr_data = await update_operational_data(self.api, ucr_data)

                LOGGER.debug(
                    "Successfully updated data for user %s (%s) ",
                    user_name,
                    ucr_id,
                )

                # set update times
                if ucr_data.get(D_ACTIVE_ALARM_COUNT, 0) > 0:
                    ucr_data[D_LAST_UPDATE_ALARM] = now
                else:
                    ucr_data[D_LAST_UPDATE_DATA] = now

            self.cluster_data[ucr_id] = ucr_data

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
        """Load new data upon changes of config_entry."""
        LOGGER.info(
            "Configuration for unit %s changed, loading new data...",
            self.cluster_name,
        )
        self.cluster_data.update(
            self.hass.config_entries.async_get_entry(entry_id).data.get(
                "user_cluster_relations", {}
            )
        )
        await self.initialize_data()

        await self.async_request_refresh()
