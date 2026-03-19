"""Coordinator for myDivera integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    UPDATE_INTERVAL_ALARM,
    UPDATE_INTERVAL_DATA,
)
from .divera_api import DiveraAPI
from .divera_data import update_data
from .utils import set_update_interval

_LOGGER = logging.getLogger(__name__)


class DiveraCoordinator(DataUpdateCoordinator):
    """Manages all data handling."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: "DiveraAPI",
        ucr_id: str,
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

        self.cluster_id: str = config_entry.data.get(D_CLUSTER_ID, "")
        self.cluster_name: str = config_entry.data.get(D_CLUSTER_NAME, "")
        self.ucr_id: str = ucr_id
        self.user_name: str = (
            ""  # Placeholder, will be set in the coordinator after fetching data
        )

        self.interval_data = {
            D_UPDATE_INTERVAL_ALARM: timedelta(
                seconds=config_entry.data.get(
                    D_UPDATE_INTERVAL_ALARM, UPDATE_INTERVAL_ALARM
                )
            ),
            D_UPDATE_INTERVAL_DATA: timedelta(
                seconds=config_entry.data.get(
                    D_UPDATE_INTERVAL_DATA, UPDATE_INTERVAL_DATA
                )
            ),
        }

        super().__init__(
            hass,
            _LOGGER,
            name=f"DiveraCoordinator_{self.ucr_id}",
            update_interval=self.interval_data.get(D_UPDATE_INTERVAL_DATA),
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Divera API.

        Returns:
            cluster_data (dict): The updated data dictionary with the latest Divera information.

        Raises:
            UpdateFailed: If there is an error fetching data from the API.

        """

        try:
            # read data from Divera API
            raw_ucr_data = await self.api.get_pull_all()
            new_cluster_data = await update_data(self.api, raw_ucr_data, self.data)

            # set user name if not already set (first update)
            # TODO Do we still need this?
            if not self.user_name:
                firstname = new_cluster_data.get("user", {}).get("firstname", "")
                lastname = new_cluster_data.get("user", {}).get("lastname", "")
                self.user_name = f"{firstname} {lastname}".strip()

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
