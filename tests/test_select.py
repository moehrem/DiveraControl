"""Tests for DiveraControl select entities."""

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.diveracontrol.const import D_CLUSTER, D_FMS_STATUS, D_VEHICLE
from custom_components.diveracontrol.select_entity import (
    DiveraVehicleStatusSelect,
    DiveraVehicleStatusSelectManager,
)


def _mock_coordinator(hass: HomeAssistant, data: dict) -> MagicMock:
    """Create a lightweight coordinator mock for entity tests."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = data
    coordinator.ucr_id = "123456"
    coordinator.cluster_name = "Test Cluster"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    coordinator.async_request_refresh = AsyncMock()
    coordinator.api = MagicMock()
    coordinator.api.post_vehicle_status = AsyncMock()
    return coordinator


def test_vehicle_status_select_options_and_current_option(hass: HomeAssistant) -> None:
    """Test options and current option are derived from coordinator data."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                D_VEHICLE: {
                    "1": {
                        "name": "LF 16",
                        "shortname": "LF",
                        "fmsstatus_id": 2,
                    }
                },
                D_FMS_STATUS: {
                    "items": {
                        "1": {"number": 1, "name": "Verfuegbar"},
                        "2": {"number": 2, "name": "Einsatzbereit"},
                    }
                },
            }
        },
    )

    entity = DiveraVehicleStatusSelect(coordinator, "1")

    assert entity.options == ["1 - Verfuegbar", "2 - Einsatzbereit"]
    assert entity.current_option == "2 - Einsatzbereit"


async def test_vehicle_status_select_posts_selected_option(
    hass: HomeAssistant,
) -> None:
    """Test selecting option posts a status update via API."""
    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                D_VEHICLE: {
                    "1": {
                        "name": "LF 16",
                        "shortname": "LF",
                        "fmsstatus_id": 1,
                    }
                },
                D_FMS_STATUS: {
                    "items": {
                        "1": {"number": 1, "name": "Verfuegbar"},
                        "2": {"number": 2, "name": "Einsatzbereit"},
                    }
                },
            }
        },
    )

    entity = DiveraVehicleStatusSelect(coordinator, "1")

    with patch.object(entity, "async_write_ha_state"):
        await entity.async_select_option("2 - Einsatzbereit")

    coordinator.api.post_vehicle_status.assert_awaited_once_with(
        1,
        {"status_id": "2"},
    )
    assert coordinator.data[D_CLUSTER][D_VEHICLE]["1"]["fmsstatus_id"] == 2
    coordinator.async_request_refresh.assert_awaited_once()


def test_vehicle_status_select_manager_adds_and_removes_entities(
    hass: HomeAssistant,
) -> None:
    """Test vehicle status select manager sync behavior on add/remove."""
    listener_holder: dict[str, Callable] = {}

    coordinator = _mock_coordinator(
        hass,
        {
            D_CLUSTER: {
                D_VEHICLE: {
                    "old_vehicle": {"name": "A", "shortname": "B"},
                },
                D_FMS_STATUS: {"items": {"1": {"number": 1, "name": "One"}}},
            }
        },
    )

    def _add_listener(listener):
        listener_holder["callback"] = listener
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)

    added_entities: list = []

    def _add_entities(entities, _update_before_add=False):
        added_entities.extend(entities)

    manager = DiveraVehicleStatusSelectManager(coordinator, "123456", _add_entities)
    manager.start()

    coordinator.data[D_CLUSTER][D_VEHICLE] = {
        "new_vehicle": {"name": "A", "shortname": "B"}
    }

    mock_registry = MagicMock()
    mock_registry.async_get_entity_id.return_value = "select.to_remove"

    with patch(
        "custom_components.diveracontrol.select_entity.er.async_get",
        return_value=mock_registry,
    ):
        listener_holder["callback"]()

    assert len(added_entities) == 2
    assert isinstance(added_entities[0], DiveraVehicleStatusSelect)
    assert isinstance(added_entities[1], DiveraVehicleStatusSelect)
    mock_registry.async_remove.assert_called_once_with("select.to_remove")
