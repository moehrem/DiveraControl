"""Definition of Home Assistant Sensors for the Divera Integration.

Responsibilities:
- Subscribe to data from the DataUpdateCoordinator (per HUB).
- Provide sensor data (state, extra_state_attributes, etc.) for Home Assistant.
- Handle attributes such as unique_id, name, etc., required for sensor integration.
- Adding and removing of sensors.

Communication:
- Retrieves data from the DataUpdateCoordinator (per HUB).
- Delivers data to Home Assistant for display in the user interface or use in automations.


"""

import asyncio
import logging
from typing import Set, Any

from homeassistant.core import HomeAssistant

from .const import (
    # general
    DOMAIN,
    MANUFACTURER,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
    # data
    D_ALARM,
    D_OPEN_ALARMS,
    D_COORDINATOR,
    D_DATA,
    D_UCR_ID,
    D_UCR,
    D_CLUSTER,
    D_VEHICLE,
    D_UCR_ID,
    D_USER,
    D_STATUS,
    D_MONITOR,
)
from .divera_entity_handling import (
    DiveraAlarmSensor,
    DiveraVehicleSensor,
    DiveraVehicleSensor,
    DiveraOpenAlarmsSensor,
    DiveraAvailabilitySensor,
    DiveraUnitSensor,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry, async_add_entities
) -> None:
    """Set up the Divera sensors."""

    ucr_id = config_entry.data[D_UCR_ID]
    coordinator = hass.data[DOMAIN][ucr_id][D_COORDINATOR]
    current_sensors = hass.data[DOMAIN][ucr_id].setdefault("sensors", {})

    async def async_add_sensor():
        """Fügt neue Sensoren hinzu."""
        cluster_data = coordinator.cluster_data
        new_sensors = []

        new_alarm_data = extract_keys(cluster_data.get(D_ALARM, {}).get("items"))
        new_vehicle_data = extract_keys(cluster_data.get(D_CLUSTER, {}).get(D_VEHICLE))
        new_availability_data = extract_keys(
            cluster_data.get(D_CLUSTER, {}).get(D_STATUS)
        )
        new_static_sensors_data = {D_OPEN_ALARMS, D_CLUSTER}

        # Alarm-Sensoren hinzufügen
        for alarm_id in new_alarm_data - current_sensors.keys():
            sensor = DiveraAlarmSensor(coordinator, alarm_id)
            new_sensors.append(sensor)
            current_sensors[alarm_id] = sensor

        # Fahrzeug-Sensoren hinzufügen
        for vehicle_id in new_vehicle_data - current_sensors.keys():
            sensor = DiveraVehicleSensor(coordinator, vehicle_id)
            new_sensors.append(sensor)
            current_sensors[vehicle_id] = sensor

        # Status-Sensoren hinzufügen
        for status_id in new_availability_data - current_sensors.keys():
            sensor = DiveraAvailabilitySensor(coordinator, status_id)
            new_sensors.append(sensor)
            current_sensors[status_id] = sensor

        # Statische Sensoren hinzufügen
        static_sensor_map = {
            D_OPEN_ALARMS: DiveraOpenAlarmsSensor(coordinator),
            D_CLUSTER: DiveraUnitSensor(coordinator),
        }

        for sensor_name, sensor_instance in static_sensor_map.items():
            if sensor_name not in current_sensors:
                new_sensors.append(sensor_instance)
                current_sensors[sensor_name] = sensor_instance

        # Sensoren zur HA-Plattform hinzufügen
        if new_sensors:
            async_add_entities(new_sensors, update_before_add=True)

    async def async_remove_sensor():
        """Entfernt Sensoren, die nicht mehr benötigt werden."""
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

    # Initialer Aufruf für Sensor-Setup
    await async_add_sensor()
    await async_remove_sensor()

    # Listener für automatische Updates registrieren
    coordinator.async_add_listener(lambda: asyncio.create_task(async_add_sensor()))
    coordinator.async_add_listener(lambda: asyncio.create_task(async_remove_sensor()))


def extract_keys(data) -> Set[str]:
    """Extrahiert Schlüsselwerte aus Dictionaries."""
    return set(data.keys()) if isinstance(data, dict) else set()
