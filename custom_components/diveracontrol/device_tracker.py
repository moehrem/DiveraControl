"""Handles all device_tracker entities."""

import asyncio
import logging
from typing import Set

from homeassistant.core import HomeAssistant

from .const import (
    D_ALARM,
    D_CLUSTER,
    D_CLUSTER_ID,
    D_COORDINATOR,
    D_UCR,
    D_UCR_ID,
    D_USER,
    D_VEHICLE,
    DOMAIN,
    I_CLOSED_ALARM,
    I_OPEN_ALARM,
    I_OPEN_ALARM_NOPRIO,
    I_VEHICLE,
    MANUFACTURER,
    MINOR_VERSION,
    PATCH_VERSION,
    VERSION,
)
from .divera_entity_handling import (
    BaseDiveraTracker,
    DiveraAlarmTracker,
    DiveraVehicleTracker,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up Divera device trackers."""

    cluster_id = config_entry.data[D_CLUSTER_ID]
    coordinator = hass.data[DOMAIN][cluster_id][D_COORDINATOR]
    current_trackers = hass.data[DOMAIN][cluster_id].setdefault("device_tracker", {})

    async def async_add_trackers():
        """Fügt neue Tracker hinzu."""
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
            async_add_entities(new_trackers, update_before_add=True)

    async def async_remove_trackers():
        """Entfernt Tracker, die nicht mehr benötigt werden."""
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

    # Initialer Aufruf für Sensor-Setup
    await async_add_trackers()
    await async_remove_trackers()

    # Listener für automatische Updates registrieren
    coordinator.async_add_listener(lambda: asyncio.create_task(async_add_trackers()))
    coordinator.async_add_listener(lambda: asyncio.create_task(async_remove_trackers()))


def extract_keys(data) -> Set[str]:
    """Extrahiert Schlüsselwerte aus Dictionaries."""
    return set(data.keys()) if isinstance(data, dict) else set()
