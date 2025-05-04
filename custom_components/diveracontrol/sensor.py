"""Definition of Home Assistant Sensors for the DiveraControl integration."""

import asyncio
from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
        hass (HomeAssistant): Home Assistant instance.
        config_entry (Config_Entry): configuration entry for the integration.
        async_add_entities (Callable): function to add entities to Home Assistant.

    Returns:
        None

    """

    ucr_id = config_entry.data[D_UCR_ID]
    coordinator = hass.data[DOMAIN][ucr_id][D_COORDINATOR]
    current_sensors = hass.data[DOMAIN][ucr_id].setdefault("sensors", {})

    async def async_add_sensor() -> None:
        """Adding new sensors.

        Retuns:
            None

        """
        cluster_data = coordinator.cluster_data
        new_sensors = []

        new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items"))
        new_vehicle_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE))
        new_availability_data = extract_keys(
            cluster_data.get(D_CLUSTER, {}).get(D_STATUS)
        )

        # adding alarm sensros
        for alarm_id in new_alarm_data - current_sensors.keys():
            sensor = DiveraAlarmSensor(coordinator, alarm_id)
            new_sensors.append(sensor)
            current_sensors[alarm_id] = sensor

        # adding vehicle sensors
        for vehicle_id in new_vehicle_data - current_sensors.keys():
            sensor = DiveraVehicleSensor(coordinator, vehicle_id)
            new_sensors.append(sensor)
            current_sensors[vehicle_id] = sensor

        # adding availability sensors
        for status_id in new_availability_data - current_sensors.keys():
            sensor = DiveraAvailabilitySensor(coordinator, status_id)
            new_sensors.append(sensor)
            current_sensors[status_id] = sensor

        # adding static sensors
        static_sensor_map = {
            D_OPEN_ALARMS: DiveraOpenAlarmsSensor(coordinator),
            D_CLUSTER: DiveraUnitSensor(coordinator),
        }

        for sensor_name, sensor_instance in static_sensor_map.items():
            if sensor_name not in current_sensors:
                new_sensors.append(sensor_instance)
                current_sensors[sensor_name] = sensor_instance

        # adding sensors to platform
        if new_sensors:
            async_add_entities(new_sensors, update_before_add=False)

    async def async_remove_sensor() -> None:
        """Remove unnnecessary sensors.

        Returns:
            None

        """
        cluster_data = coordinator.cluster_data

        new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items"))
        new_vehicle_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE))
        new_status_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_STATUS))
        new_static_sensors_data = {D_OPEN_ALARMS, D_CLUSTER}

        active_ids = (
            new_alarm_data
            | new_vehicle_data
            | new_status_data
            | new_static_sensors_data
        )
        removable_sensors = set(current_sensors.keys()) - active_ids

        remove_tasks = []
        for sensor_id in removable_sensors:
            sensor = current_sensors.pop(sensor_id, None)
            if sensor:
                remove_tasks.append(sensor.remove_from_hass())
                _LOGGER.debug("Removed sensor: %s", sensor_id)

        if remove_tasks:
            await asyncio.gather(*remove_tasks)

    await async_add_sensor()
    await async_remove_sensor()

    # register listeners for automatic updates
    coordinator.async_add_listener(lambda: asyncio.create_task(async_add_sensor()))
    coordinator.async_add_listener(lambda: asyncio.create_task(async_remove_sensor()))
