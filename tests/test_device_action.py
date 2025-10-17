"""Tests for the DiveraControl device_action module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.helpers import device_registry as dr

from custom_components.diveracontrol.const import (
    D_UCR_ID,
    DOMAIN,
    PERM_ALARM,
    PERM_MANAGEMENT,
    PERM_STATUS_VEHICLE,
)
from custom_components.diveracontrol.device_action import (
    ACTION_SCHEMA,
    ACTION_TYPES,
    async_call_action_from_config,
    async_get_action_capabilities,
    async_get_actions,
    async_validate_action_config,
)


@pytest.fixture
def mock_device_registry(hass):
    """Create a mock device registry."""
    registry = dr.async_get(hass)
    return registry


@pytest.fixture
def mock_device(hass, mock_device_registry, mock_config_entry):
    """Create a mock device."""
    # Config entry must exist first
    mock_config_entry.add_to_hass(hass)

    device = mock_device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "test_device")},
        name="Test Device",
    )
    return device


@pytest.fixture
def mock_config_entry(hass):
    """Create a mock config entry."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={D_UCR_ID: "test_ucr_id"},
        unique_id="test_unique_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_coordinator_data():
    """Create mock coordinator data."""
    return {
        "cluster": {
            "vehicle": {
                "items": {
                    1: {"name": "Vehicle 1", "shortname": "V1"},
                    2: {"name": "Vehicle 2", "shortname": "V2"},
                }
            },
            "fms_status": {
                "items": {
                    1: {"number": 1, "name": "Available"},
                    2: {"number": 2, "name": "En Route"},
                }
            },
            "consumer": {
                "items": {
                    10: {"firstname": "John", "lastname": "Doe"},
                    20: {"firstname": "Jane", "lastname": "Smith"},
                }
            },
            "group": {
                "items": {
                    100: {"name": "Group 1"},
                    200: {"name": "Group 2"},
                }
            },
            "status": {
                "items": {
                    1: {"name": "On Duty"},
                    2: {"name": "Off Duty"},
                }
            },
            "alarmcode": {
                "items": {
                    1: {"name": "Fire"},
                    2: {"name": "Medical"},
                }
            },
        },
        "alarm": {
            "items": {
                500: {"title": "Test Alarm", "id": 500},
            }
        },
    }


class TestActionTypes:
    """Test ACTION_TYPES constant."""

    def test_action_types_defined(self):
        """Test that all expected action types are defined."""
        expected_types = (
            "post_vehicle_status",
            "post_alarm",
            "put_alarm",
            "post_close_alarm",
            "post_message",
            "post_using_vehicle_property",
            "post_using_vehicle_crew",
            "post_news",
        )
        assert ACTION_TYPES == expected_types


class TestActionSchema:
    """Test ACTION_SCHEMA validation."""

    def test_valid_schema(self):
        """Test valid action schema."""
        config = {
            "domain": DOMAIN,
            "type": "post_vehicle_status",
            "device_id": "test_device",
        }
        result = ACTION_SCHEMA(config)
        assert result["domain"] == DOMAIN
        assert result["type"] == "post_vehicle_status"

    def test_invalid_type(self):
        """Test invalid action type."""
        config = {
            "domain": DOMAIN,
            "type": "invalid_action",
        }
        with pytest.raises(vol.Invalid):
            ACTION_SCHEMA(config)

    def test_missing_required_fields(self):
        """Test missing required fields."""
        config = {"domain": DOMAIN}
        with pytest.raises(vol.Invalid):
            ACTION_SCHEMA(config)


class TestGetSelectorOptions:
    """Test _get_selector_options function."""

    @patch("custom_components.diveracontrol.device_action.get_translation")
    async def test_notification_type_options(self, mock_get_translation, hass):
        """Test notification_type_options static options."""
        mock_get_translation.side_effect = ["Type 1", "Type 2", "Type 3", "Type 4"]

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(
            hass, "test_device", "notification_type_options"
        )

        assert len(options) == 4
        assert options[0] == {"value": "1", "label": "Type 1"}
        assert options[1] == {"value": "2", "label": "Type 2"}
        assert options[2] == {"value": "3", "label": "Type 3"}
        assert options[3] == {"value": "4", "label": "Type 4"}

        # Verify translation calls
        expected_calls = [
            ((hass, "selector", "notification_type_options.options.1"),),
            ((hass, "selector", "notification_type_options.options.2"),),
            ((hass, "selector", "notification_type_options.options.3"),),
            ((hass, "selector", "notification_type_options.options.4"),),
        ]
        mock_get_translation.assert_has_calls(expected_calls)

    @patch("custom_components.diveracontrol.device_action.get_translation")
    async def test_mode_options(self, mock_get_translation, hass):
        """Test mode_options static options."""
        mock_get_translation.side_effect = ["Add", "Remove", "Reset"]

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(hass, "test_device", "mode_options")

        assert len(options) == 3
        assert options[0] == {"value": "add", "label": "Add"}
        assert options[1] == {"value": "remove", "label": "Remove"}
        assert options[2] == {"value": "reset", "label": "Reset"}

        # Verify translation calls
        expected_calls = [
            ((hass, "selector", "mode_options.options.add"),),
            ((hass, "selector", "mode_options.options.remove"),),
            ((hass, "selector", "mode_options.options.reset"),),
        ]
        mock_get_translation.assert_has_calls(expected_calls)

    @patch("custom_components.diveracontrol.device_action.get_translation")
    async def test_newssurvey_result_count_options(self, mock_get_translation, hass):
        """Test newssurvey_show_result_count_options static options."""
        mock_get_translation.side_effect = ["Option 0", "Option 1", "Option 2"]

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(
            hass, "test_device", "newssurvey_show_result_count_options"
        )

        assert len(options) == 3
        assert options[0] == {"value": "0", "label": "Option 0"}
        assert options[1] == {"value": "1", "label": "Option 1"}
        assert options[2] == {"value": "2", "label": "Option 2"}

    @patch("custom_components.diveracontrol.device_action.get_translation")
    async def test_newssurvey_result_names_options(self, mock_get_translation, hass):
        """Test newssurvey_show_result_names_options static options."""
        mock_get_translation.side_effect = ["Option 0", "Option 1", "Option 2"]

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(
            hass, "test_device", "newssurvey_show_result_names_options"
        )

        assert len(options) == 3
        assert options[0] == {"value": "0", "label": "Option 0"}
        assert options[1] == {"value": "1", "label": "Option 1"}
        assert options[2] == {"value": "2", "label": "Option 2"}

    @patch(
        "custom_components.diveracontrol.device_action.get_coordinator_key_from_device"
    )
    async def test_dynamic_options_from_coordinator(self, mock_get_coordinator, hass):
        """Test dynamic options retrieved from coordinator data."""
        # Mock coordinator data
        mock_coordinator_data = {
            "cluster": {
                "vehicle": {
                    "items": {
                        1: {"name": "Vehicle 1", "shortname": "V1"},
                        2: {"name": "Vehicle 2", "shortname": "V2"},
                    }
                }
            }
        }
        mock_get_coordinator.return_value = mock_coordinator_data

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(
            hass, "test_device", "cluster.vehicle", "{name} / {shortname}"
        )

        assert len(options) == 2
        assert options[0] == {"value": "1", "label": "Vehicle 1 / V1"}
        assert options[1] == {"value": "2", "label": "Vehicle 2 / V2"}

    @patch(
        "custom_components.diveracontrol.device_action.get_coordinator_key_from_device"
    )
    async def test_dynamic_options_empty_device_id(self, mock_get_coordinator, hass):
        """Test dynamic options with empty device_id."""
        mock_get_coordinator.return_value = {}

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(hass, "", "cluster.vehicle")

        assert options == []
        mock_get_coordinator.assert_called_once_with(hass, "", "data")

    @patch(
        "custom_components.diveracontrol.device_action.get_coordinator_key_from_device"
    )
    async def test_dynamic_options_no_data(self, mock_get_coordinator, hass):
        """Test dynamic options when no data is available."""
        mock_get_coordinator.return_value = {}

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(hass, "test_device", "cluster.vehicle")

        assert options == []

    @patch(
        "custom_components.diveracontrol.device_action.get_coordinator_key_from_device"
    )
    async def test_dynamic_options_no_items(self, mock_get_coordinator, hass):
        """Test dynamic options when data has no items wrapper."""
        mock_coordinator_data = {
            "cluster": {
                "vehicle": {}  # No items wrapper
            }
        }
        mock_get_coordinator.return_value = mock_coordinator_data

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(hass, "test_device", "cluster.vehicle")

        assert options == []

    @patch(
        "custom_components.diveracontrol.device_action.get_coordinator_key_from_device"
    )
    async def test_dynamic_options_default_label_format(
        self, mock_get_coordinator, hass
    ):
        """Test dynamic options with default label format (None)."""
        mock_coordinator_data = {
            "cluster": {
                "vehicle": {
                    "items": {
                        1: {"name": "Vehicle 1"},
                        2: {"name": "Vehicle 2"},
                    }
                }
            }
        }
        mock_get_coordinator.return_value = mock_coordinator_data

        from custom_components.diveracontrol.device_action import _get_selector_options

        options = await _get_selector_options(
            hass, "test_device", "cluster.vehicle", None
        )

        assert len(options) == 2
        assert options[0] == {"value": "1", "label": "Vehicle 1"}
        assert options[1] == {"value": "2", "label": "Vehicle 2"}


class TestAsyncGetActions:
    """Test async_get_actions function."""

    @patch("custom_components.diveracontrol.device_action.permission_check")
    async def test_get_actions_with_management_permission(
        self, mock_permission, hass, mock_device, mock_config_entry
    ):
        """Test getting actions with management permission."""
        mock_permission.return_value = True

        actions = await async_get_actions(hass, mock_device.id)

        assert len(actions) == 8
        assert all(action["domain"] == DOMAIN for action in actions)
        assert all(action["device_id"] == mock_device.id for action in actions)

    @patch("custom_components.diveracontrol.device_action.permission_check")
    async def test_get_actions_with_specific_permissions(
        self, mock_permission, hass, mock_device, mock_config_entry
    ):
        """Test getting actions with specific permissions."""

        def permission_side_effect(hass, ucr_id, perm):
            if perm == PERM_MANAGEMENT:
                return False
            if perm == PERM_STATUS_VEHICLE:
                return True
            if perm == PERM_ALARM:
                return True
            return False

        mock_permission.side_effect = permission_side_effect

        actions = await async_get_actions(hass, mock_device.id)

        action_types = [action["type"] for action in actions]
        assert "post_vehicle_status" in action_types
        assert "post_alarm" in action_types
        assert "post_message" not in action_types  # No PERM_MESSAGES

    @patch("custom_components.diveracontrol.device_action.permission_check")
    async def test_get_actions_no_permissions(
        self, mock_permission, hass, mock_device, mock_config_entry
    ):
        """Test getting actions with no permissions."""
        mock_permission.return_value = False

        actions = await async_get_actions(hass, mock_device.id)

        assert len(actions) == 0

    async def test_get_actions_invalid_device(self, hass):
        """Test getting actions for invalid device."""
        actions = await async_get_actions(hass, "nonexistent_device")

        assert actions == []


class TestAsyncCallActionFromConfig:
    """Test async_call_action_from_config function."""

    async def test_call_action_success(self, hass):
        """Test successful action call."""
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        config = {
            "domain": DOMAIN,
            "type": "post_vehicle_status",
            "device_id": "test_device",
            "vehicle_id": [1],
            "status": 2,
        }

        await async_call_action_from_config(hass, config, {}, None)

        hass.services.async_call.assert_called_once()
        call_args = hass.services.async_call.call_args
        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == "post_vehicle_status"
        assert call_args[0][2]["device_id"] == "test_device"
        assert call_args[0][2]["vehicle_id"] == [1]

    async def test_call_action_with_data_dict(self, hass):
        """Test action call with data dict."""
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()

        config = {
            "domain": DOMAIN,
            "type": "post_alarm",
            "device_id": "test_device",
            "data": {"title": "Test", "notification_type": 1},
        }

        await async_call_action_from_config(hass, config, {}, None)

        call_args = hass.services.async_call.call_args[0][2]
        assert call_args["title"] == "Test"
        assert call_args["notification_type"] == 1

    async def test_call_action_invalid_config(self, hass):
        """Test action call with invalid config."""
        config = {
            "domain": DOMAIN,
            "type": "invalid_action",
            "device_id": "test_device",
        }

        with pytest.raises(InvalidDeviceAutomationConfig):
            await async_call_action_from_config(hass, config, {}, None)


class TestAsyncValidateActionConfig:
    """Test async_validate_action_config function."""

    async def test_validate_valid_config(self, hass):
        """Test validating valid config."""
        config = {
            "domain": DOMAIN,
            "type": "post_vehicle_status",
            "device_id": "test_device",
        }

        result = await async_validate_action_config(hass, config)

        assert result["domain"] == DOMAIN
        assert result["type"] == "post_vehicle_status"

    async def test_validate_invalid_config(self, hass):
        """Test validating invalid config."""
        config = {"domain": DOMAIN}

        with pytest.raises(vol.Invalid):
            await async_validate_action_config(hass, config)


class TestAsyncGetActionCapabilities:
    """Test async_get_action_capabilities function."""

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_post_vehicle_status(self, mock_get_options, hass):
        """Test capabilities for post_vehicle_status."""
        mock_get_options.side_effect = [
            [{"value": "1", "label": "Vehicle 1"}],  # vehicle_options
            [{"value": "1", "label": "1 - Available"}],  # fms_status_options
        ]

        config = {
            "type": "post_vehicle_status",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result
        assert isinstance(result["extra_fields"], vol.Schema)

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_post_alarm(self, mock_get_options, hass):
        """Test capabilities for post_alarm."""
        mock_get_options.side_effect = [
            [{"value": "1", "label": "Type 1"}],  # notification_type
            [{"value": "1", "label": "Vehicle 1"}],  # vehicles
            [{"value": "1", "label": "User 1"}],  # users
            [{"value": "1", "label": "Group 1"}],  # groups
            [{"value": "1", "label": "Status 1"}],  # statuses
            [{"value": "1", "label": "Code 1"}],  # alarmcodes
            [],  # alarms
        ]

        config = {
            "type": "post_alarm",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_put_alarm(self, mock_get_options, hass):
        """Test capabilities for put_alarm with alarm_id."""
        mock_get_options.side_effect = [
            [{"value": "1", "label": "Type 1"}],  # notification_type
            [{"value": "1", "label": "Vehicle 1"}],  # vehicles
            [{"value": "1", "label": "User 1"}],  # users
            [{"value": "1", "label": "Group 1"}],  # groups
            [{"value": "1", "label": "Status 1"}],  # statuses
            [{"value": "1", "label": "Code 1"}],  # alarmcodes
            [{"value": "500", "label": "Alarm 500"}],  # alarms
        ]

        config = {
            "type": "put_alarm",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_post_close_alarm(self, mock_get_options, hass):
        """Test capabilities for post_close_alarm."""
        mock_get_options.return_value = [{"value": "500", "label": "Alarm 500"}]

        config = {
            "type": "post_close_alarm",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_post_message(self, mock_get_options, hass):
        """Test capabilities for post_message."""
        mock_get_options.side_effect = [
            [],  # alarm_options
            [],  # message_channel_options (if needed)
        ]

        config = {
            "type": "post_message",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_post_using_vehicle_property(
        self, mock_get_options, hass
    ):
        """Test capabilities for post_using_vehicle_property."""
        mock_get_options.return_value = [{"value": "1", "label": "Vehicle 1"}]

        config = {
            "type": "post_using_vehicle_property",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_post_using_vehicle_crew(self, mock_get_options, hass):
        """Test capabilities for post_using_vehicle_crew."""
        mock_get_options.side_effect = [
            [{"value": "1", "label": "Vehicle 1"}],  # vehicles
            [{"value": "10", "label": "User 1"}],  # crew
            [{"value": "add", "label": "Add"}],  # modes
        ]

        config = {
            "type": "post_using_vehicle_crew",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result

    @patch("custom_components.diveracontrol.device_action._get_selector_options")
    async def test_capabilities_post_news(self, mock_get_options, hass):
        """Test capabilities for post_news."""
        mock_get_options.side_effect = [
            [{"value": "1", "label": "Type 1"}],  # notification_type
            [{"value": "1", "label": "Group 1"}],  # groups
            [{"value": "1", "label": "User 1"}],  # users
            [{"value": "0", "label": "Option 0"}],  # show_result_count
            [{"value": "0", "label": "Option 0"}],  # show_result_names
        ]

        config = {
            "type": "post_news",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert "extra_fields" in result

    async def test_capabilities_missing_type(self, hass):
        """Test capabilities with missing type."""
        config = {"device_id": "test_device"}

        result = await async_get_action_capabilities(hass, config)

        assert result == {}

    async def test_capabilities_missing_device_id(self, hass):
        """Test capabilities with missing device_id."""
        config = {"type": "post_vehicle_status"}

        result = await async_get_action_capabilities(hass, config)

        assert result == {}

    async def test_capabilities_unknown_action_type(self, hass):
        """Test capabilities for unknown action type."""
        config = {
            "type": "unknown_action",
            "device_id": "test_device",
        }

        result = await async_get_action_capabilities(hass, config)

        assert result == {}
