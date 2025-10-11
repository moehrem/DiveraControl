# """Definition of Home Assistant Sensors for the DiveraControl integration."""

# import asyncio
# from collections.abc import Callable
# import logging

# from homeassistant.config_entries import ConfigEntry
# from homeassistant.core import HomeAssistant

# from .const import (
#     D_ALARM,
#     D_CLUSTER,
#     D_COORDINATOR,
#     D_OPEN_ALARMS,
#     D_STATUS,
#     D_UCR_ID,
#     D_VEHICLE,
#     DOMAIN,
# )
# from .entity import (
#     DiveraAlarmSensor,
#     DiveraAvailabilitySensor,
#     DiveraOpenAlarmsSensor,
#     DiveraUnitSensor,
#     DiveraVehicleSensor,
# )
# from .utils import extract_keys

# _LOGGER = logging.getLogger(__name__)


# async def async_setup_entry(
#     hass: HomeAssistant,
#     config_entry: ConfigEntry,
#     async_add_entities: Callable,
# ) -> None:
#     """Set up the Divera sensors.

#     Args:
#         hass (HomeAssistant): Home Assistant instance.
#         config_entry (Config_Entry): configuration entry for the integration.
#         async_add_entities (Callable): function to add entities to Home Assistant.

#     Returns:
#         None

#     """

#     ucr_id = config_entry.data[D_UCR_ID]
#     coordinator = hass.data[DOMAIN][ucr_id][D_COORDINATOR]
#     current_sensors = hass.data[DOMAIN][ucr_id].setdefault("sensors", {})

#     async def async_add_sensor() -> None:
#         """Adding new sensors.

#         Retuns:
#             None

#         """
#         cluster_data = coordinator.data
#         new_sensors = []

#         new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items"))
#         new_vehicle_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE))
#         new_availability_data = extract_keys(
#             cluster_data.get(D_CLUSTER, {}).get(D_STATUS)
#         )

#         # adding alarm sensros
#         for alarm_id in new_alarm_data - current_sensors.keys():
#             sensor = DiveraAlarmSensor(coordinator, alarm_id)
#             new_sensors.append(sensor)
#             current_sensors[alarm_id] = sensor

#         # adding vehicle sensors
#         for vehicle_id in new_vehicle_data - current_sensors.keys():
#             sensor = DiveraVehicleSensor(coordinator, vehicle_id)
#             new_sensors.append(sensor)
#             current_sensors[vehicle_id] = sensor

#         # adding availability sensors
#         for status_id in new_availability_data - current_sensors.keys():
#             sensor = DiveraAvailabilitySensor(coordinator, status_id)
#             new_sensors.append(sensor)
#             current_sensors[status_id] = sensor

#         # adding static sensors
#         static_sensor_map = {
#             D_OPEN_ALARMS: DiveraOpenAlarmsSensor(coordinator),
#             D_CLUSTER: DiveraUnitSensor(coordinator),
#         }

#         for sensor_name, sensor_instance in static_sensor_map.items():
#             if sensor_name not in current_sensors:
#                 new_sensors.append(sensor_instance)
#                 current_sensors[sensor_name] = sensor_instance

#         # adding sensors to platform
#         if new_sensors:
#             async_add_entities(new_sensors, update_before_add=False)

#     async def async_remove_sensor() -> None:
#         """Remove unnnecessary sensors.

#         Returns:
#             None

#         """
#         cluster_data = coordinator.data

#         new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items"))
#         new_vehicle_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE))
#         new_status_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_STATUS))
#         new_static_sensors_data = {D_OPEN_ALARMS, D_CLUSTER}

#         active_ids = (
#             new_alarm_data
#             | new_vehicle_data
#             | new_status_data
#             | new_static_sensors_data
#         )
#         removable_sensors = set(current_sensors.keys()) - active_ids

#         remove_tasks = []
#         for sensor_id in removable_sensors:
#             sensor = current_sensors.pop(sensor_id, None)
#             if sensor:
#                 remove_tasks.append(sensor.remove_from_hass())
#                 _LOGGER.debug("Removed sensor: %s", sensor_id)

#         if remove_tasks:
#             await asyncio.gather(*remove_tasks)

#     await async_add_sensor()
#     await async_remove_sensor()

#     # register listeners for automatic updates
#     coordinator.async_add_listener(lambda: asyncio.create_task(async_add_sensor()))
#     coordinator.async_add_listener(lambda: asyncio.create_task(async_remove_sensor()))


"""Definition of Home Assistant Sensors for the DiveraControl integration."""

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    D_ALARM,
    D_CLUSTER,
    D_COORDINATOR,
    D_OPEN_ALARMS,
    D_STATUS,
    D_UCR_ID,
    D_VEHICLE,
    DOMAIN,
)
from .coordinator import DiveraCoordinator
from .entity import (
    DiveraAlarmSensor,
    DiveraAvailabilitySensor,
    DiveraOpenAlarmsSensor,
    DiveraUnitSensor,
    DiveraVehicleSensor,
)
from .utils import extract_keys

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up the Divera sensors.

    Args:
        hass: Home Assistant instance.
        config_entry: Configuration entry for the integration.
        async_add_entities: Function to add entities to Home Assistant.

    """
    ucr_id = config_entry.data[D_UCR_ID]
    coordinator: DiveraCoordinator = hass.data[DOMAIN][ucr_id][D_COORDINATOR]

    # Track known IDs
    known_alarm_ids: set[str] = set()
    known_vehicle_ids: set[str] = set()
    known_status_ids: set[str] = set()
    known_static_sensors: set[str] = set()

    @callback
    def _async_update_sensors() -> None:
        """Add new sensors and remove archived ones."""
        cluster_data = coordinator.data

        # Get current IDs from data
        current_alarm_ids = extract_keys(cluster_data.get(D_ALARM, {}).get("items", {}))
        current_vehicle_ids = extract_keys(
            cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE, {})
        )
        current_status_ids = extract_keys(
            cluster_data.get(D_CLUSTER, {}).get(D_STATUS, {})
        )

        # FIRST: Remove archived alarm sensors
        archived_alarm_ids = known_alarm_ids - current_alarm_ids
        if archived_alarm_ids:
            entity_registry = er.async_get(hass)
            for alarm_id in archived_alarm_ids:
                unique_id = f"{ucr_id}_alarm_{alarm_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed alarm sensor: %s", alarm_id)
            known_alarm_ids.difference_update(archived_alarm_ids)

        # SECOND: Remove archived vehicle sensors
        archived_vehicle_ids = known_vehicle_ids - current_vehicle_ids
        if archived_vehicle_ids:
            entity_registry = er.async_get(hass)
            for vehicle_id in archived_vehicle_ids:
                unique_id = f"{ucr_id}_vehicle_{vehicle_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed vehicle sensor: %s", vehicle_id)
            known_vehicle_ids.difference_update(archived_vehicle_ids)

        # THIRD: Remove archived availability sensors
        archived_status_ids = known_status_ids - current_status_ids
        if archived_status_ids:
            entity_registry = er.async_get(hass)
            for status_id in archived_status_ids:
                unique_id = f"{ucr_id}_availability_{status_id}"
                entity_id = entity_registry.async_get_entity_id(
                    "sensor", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed availability sensor: %s", status_id)
            known_status_ids.difference_update(archived_status_ids)

        # FOURTH: Add new alarm sensors AFTER removal
        new_alarm_ids = current_alarm_ids - known_alarm_ids
        if new_alarm_ids:
            new_sensors = [
                DiveraAlarmSensor(coordinator, alarm_id) for alarm_id in new_alarm_ids
            ]
            async_add_entities(new_sensors, update_before_add=False)
            known_alarm_ids.update(new_alarm_ids)
            _LOGGER.debug("Added %d alarm sensors", len(new_alarm_ids))

        # FIFTH: Add new vehicle sensors AFTER removal
        new_vehicle_ids = current_vehicle_ids - known_vehicle_ids
        if new_vehicle_ids:
            new_sensors = [
                DiveraVehicleSensor(coordinator, vehicle_id)
                for vehicle_id in new_vehicle_ids
            ]
            async_add_entities(new_sensors, update_before_add=False)
            known_vehicle_ids.update(new_vehicle_ids)
            _LOGGER.debug("Added %d vehicle sensors", len(new_vehicle_ids))

        # SIXTH: Add new availability sensors AFTER removal
        new_status_ids = current_status_ids - known_status_ids
        if new_status_ids:
            new_sensors = [
                DiveraAvailabilitySensor(coordinator, status_id)
                for status_id in new_status_ids
            ]
            async_add_entities(new_sensors, update_before_add=False)
            known_status_ids.update(new_status_ids)
            _LOGGER.debug("Added %d availability sensors", len(new_status_ids))

        # SEVENTH: Add static sensors (only once)
        static_sensor_map = {
            D_OPEN_ALARMS: DiveraOpenAlarmsSensor(coordinator),
            D_CLUSTER: DiveraUnitSensor(coordinator),
        }

        new_static_sensors = []
        for sensor_key, sensor_instance in static_sensor_map.items():
            if sensor_key not in known_static_sensors:
                new_static_sensors.append(sensor_instance)
                known_static_sensors.add(sensor_key)

        if new_static_sensors:
            async_add_entities(new_static_sensors, update_before_add=False)
            _LOGGER.debug("Added %d static sensors", len(new_static_sensors))

    # Initial setup
    _async_update_sensors()

    # Register single listener for updates
    config_entry.async_on_unload(coordinator.async_add_listener(_async_update_sensors))
