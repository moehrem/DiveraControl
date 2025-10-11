"""Handles all device_tracker entities."""

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .coordinator import DiveraCoordinator

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

    ucr_id: str = config_entry.data[D_UCR_ID]
    coordinator: DiveraCoordinator = hass.data[DOMAIN][ucr_id][D_COORDINATOR]
    current_trackers = hass.data[DOMAIN][ucr_id].setdefault("device_tracker", {})

    # async def async_add_trackers() -> None:
    #     """Add new tracker.

    #     Returns:
    #         None

    #     """

    #     cluster_data = coordinator.data
    #     new_trackers = []

    #     new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items", {}))
    #     new_vehicle_data = extract_keys(
    #         cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
    #     )

    #     # add alarm trackers
    #     for alarm_id in new_alarm_data - current_trackers.keys():
    #         tracker = DiveraAlarmTracker(coordinator, alarm_id)
    #         new_trackers.append(tracker)
    #         current_trackers[alarm_id] = tracker

    #     # add vehicle trackers
    #     for vehicle_id in new_vehicle_data - current_trackers.keys():
    #         tracker = DiveraVehicleTracker(coordinator, vehicle_id)
    #         new_trackers.append(tracker)
    #         current_trackers[vehicle_id] = tracker

    #     if new_trackers:
    #         async_add_entities(new_trackers, update_before_add=False)

    # async def async_remove_trackers() -> None:
    #     """Remove unused tracker.

    #     Returns:
    #         None

    #     """

    #     cluster_data = coordinator.data

    #     new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items", {}))
    #     new_vehicle_data = extract_keys(
    #         cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
    #     )

    #     active_ids = new_alarm_data | new_vehicle_data
    #     removable_trackers = set(current_trackers.keys() - active_ids)

    #     remove_tasks = []
    #     for sensor_id in removable_trackers:
    #         sensor = current_trackers.pop(sensor_id, None)
    #         if sensor:
    #             remove_tasks.append(sensor.remove_from_hass())
    #             _LOGGER.debug("Removed tracker: %s", sensor_id)

    #     if remove_tasks:
    #         await asyncio.gather(*remove_tasks)

    # await async_add_trackers()
    # await async_remove_trackers()

    # # register listeners for auto updates of trackers
    # coordinator.async_add_listener(lambda: asyncio.create_task(async_add_trackers()))
    # coordinator.async_add_listener(lambda: asyncio.create_task(async_remove_trackers()))

    # Track known IDs
    known_alarm_ids: set[str] = set()
    known_vehicle_ids: set[str] = set()

    @callback
    def _async_update_trackers() -> None:
        """Add new trackers and remove archived ones."""
        cluster_data = coordinator.data

        # Get current IDs from data
        current_alarm_ids = extract_keys(cluster_data.get(D_ALARM, {}).get("items", {}))
        current_vehicle_ids = extract_keys(
            cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
        )

        # FIRST Remove archived alarm trackers
        archived_alarm_ids = known_alarm_ids - current_alarm_ids
        if archived_alarm_ids:
            entity_registry = er.async_get(hass)
            for alarm_id in archived_alarm_ids:
                unique_id = f"{ucr_id}_alarmtracker_{alarm_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "device_tracker", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed alarm tracker: %s", alarm_id)
            known_alarm_ids.difference_update(archived_alarm_ids)

        # SECOND Remove archived vehicle trackers
        archived_vehicle_ids = known_vehicle_ids - current_vehicle_ids
        if archived_vehicle_ids:
            entity_registry = er.async_get(hass)
            for vehicle_id in archived_vehicle_ids:
                unique_id = f"{ucr_id}_vehicletracker_{vehicle_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "device_tracker", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed vehicle tracker: %s", vehicle_id)
            known_vehicle_ids.difference_update(archived_vehicle_ids)

        # THIRD Add new alarms AFTER removal
        new_alarm_ids = current_alarm_ids - known_alarm_ids
        if new_alarm_ids:
            new_trackers = [
                DiveraAlarmTracker(coordinator, alarm_id) for alarm_id in new_alarm_ids
            ]
            async_add_entities(new_trackers, update_before_add=False)
            known_alarm_ids.update(new_alarm_ids)
            _LOGGER.debug("Added %d alarm trackers", len(new_alarm_ids))

        # FOURTH Add new vehicles AFTER removal
        new_vehicle_ids = current_vehicle_ids - known_vehicle_ids
        if new_vehicle_ids:
            new_trackers = [
                DiveraVehicleTracker(coordinator, vehicle_id)
                for vehicle_id in new_vehicle_ids
            ]
            async_add_entities(new_trackers, update_before_add=False)
            known_vehicle_ids.update(new_vehicle_ids)
            _LOGGER.debug("Added %d vehicle trackers", len(new_vehicle_ids))

    # Initial setup
    _async_update_trackers()

    # Register single listener for updates
    config_entry.async_on_unload(coordinator.async_add_listener(_async_update_trackers))
