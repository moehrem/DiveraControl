"""Handles all device_tracker entities."""

import asyncio
from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import D_ALARM, D_CLUSTER, D_COORDINATOR, D_UCR_ID, D_VEHICLE, DOMAIN
from .entity import DiveraAlarmTracker, DiveraVehicleTracker
from .utils import extract_keys

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up Divera device trackers.

    Args:
        hass (HomeAssistant): Home Assistant instance.
        config_entry (ConfigEntry): The config entry to set up.
        async_add_entities (Callable): Function to add entities.

    Returns:
        None

    """

    ucr_id = config_entry.data[D_UCR_ID]
    coordinator = hass.data[DOMAIN][ucr_id][D_COORDINATOR]
    current_trackers = hass.data[DOMAIN][ucr_id].setdefault("device_tracker", {})

    async def async_add_trackers() -> None:
        """Add new tracker.

        Returns:
            None

        """

        cluster_data = coordinator.cluster_data
        new_trackers = []

        new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items", {}))
        new_vehicle_data = extract_keys(
            cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
        )

        # add alarm trackers
        for alarm_id in new_alarm_data - current_trackers.keys():
            tracker = DiveraAlarmTracker(coordinator, alarm_id)
            new_trackers.append(tracker)
            current_trackers[alarm_id] = tracker

        # add vehicle trackers
        for vehicle_id in new_vehicle_data - current_trackers.keys():
            tracker = DiveraVehicleTracker(coordinator, vehicle_id)
            new_trackers.append(tracker)
            current_trackers[vehicle_id] = tracker

        if new_trackers:
            async_add_entities(new_trackers, update_before_add=False)

    async def async_remove_trackers() -> None:
        """Remove unused tracker.

        Returns:
            None

        """

        cluster_data = coordinator.cluster_data

        new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items", {}))
        new_vehicle_data = extract_keys(
            cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
        )

        active_ids = new_alarm_data | new_vehicle_data
        removable_trackers = set(current_trackers.keys() - active_ids)

        remove_tasks = []
        for sensor_id in removable_trackers:
            sensor = current_trackers.pop(sensor_id, None)
            if sensor:
                remove_tasks.append(sensor.remove_from_hass())
                _LOGGER.debug("Removed tracker: %s", sensor_id)

        if remove_tasks:
            await asyncio.gather(*remove_tasks)

    await async_add_trackers()
    await async_remove_trackers()

    # register listeners for auto updates of trackers
    coordinator.async_add_listener(lambda: asyncio.create_task(async_add_trackers()))
    coordinator.async_add_listener(lambda: asyncio.create_task(async_remove_trackers()))
