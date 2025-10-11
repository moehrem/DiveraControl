"""Coordinator for myDivera integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    D_CLUSTER_NAME,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
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
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize DiveraControl coordinator.

        Args:
            hass (HomeAssistant): Home Assistant instance.
            api (DiveraAPI): Divera API instance.
            config_entry (dict): Configuration entry for the integration.

        Returns:
            None

        """

        self.api = api

        self.cluster_name: str = config_entry.data.get(D_CLUSTER_NAME)
        self.ucr_id: str = config_entry.data.get(D_UCR_ID)

        self.interval_data = {
            D_UPDATE_INTERVAL_ALARM: timedelta(
                seconds=config_entry.data.get(D_UPDATE_INTERVAL_ALARM)
            ),
            D_UPDATE_INTERVAL_DATA: timedelta(
                seconds=config_entry.data.get(D_UPDATE_INTERVAL_DATA)
            ),
        }

        super().__init__(
            hass,
            _LOGGER,
            name=f"DiveraCoordinator_{self.ucr_id}",
            update_interval=self.interval_data.get(D_UPDATE_INTERVAL_DATA),
            config_entry=config_entry,
        )

    @log_execution_time
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API.

        Returns:
            cluster_data (dict): The updated data dictionary with the latest Divera information.

        Raises:
            UpdateFailed: If there is an error fetching data from the API.

        """

        try:
            # read data from Divera API
            new_cluster_data = await update_data(self.api, self.data)

            # dynamically change update interval
            self.update_interval = set_update_interval(
                new_cluster_data, self.interval_data, self.update_interval
            )

            _LOGGER.debug(
                "Successfully updated data for unit '%s'",
                self.cluster_name,
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
        else:
            return new_cluster_data
