"""Tests for DiveraControl utils.py."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.diveracontrol.const import (
    D_ACCESS,
    D_ALARM,
    D_CLUSTER,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_OPEN_ALARMS,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USER,
    D_VEHICLE,
    DOMAIN,
    MANUFACTURER,
    PERM_MANAGEMENT,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
)
from custom_components.diveracontrol.utils import (
    get_coordinator_key_from_device,
    get_device_info,
    get_translation,
    handle_entity,
    permission_check,
    set_update_interval,
)


class TestPermissionCheck:
    """Test the permission_check function."""

    def test_permission_check_management_granted(self, hass: HomeAssistant) -> None:
        """Test permission check with management permission granted."""
        mock_coordinator = MagicMock()
        mock_coordinator.cluster_name = "Test Cluster"
        mock_coordinator.data = {
            D_USER: {D_ACCESS: {PERM_MANAGEMENT: True, "some_perm": False}}
        }

        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        result = permission_check(hass, "123", "some_perm")

        assert result is True

    def test_permission_check_specific_granted(self, hass: HomeAssistant) -> None:
        """Test permission check with specific permission granted."""
        mock_coordinator = MagicMock()
        mock_coordinator.cluster_name = "Test Cluster"
        mock_coordinator.data = {
            D_USER: {D_ACCESS: {PERM_MANAGEMENT: False, "test_perm": True}}
        }

        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        result = permission_check(hass, "123", "test_perm")

        assert result is False  # Function returns False when permission granted

    def test_permission_check_denied(self, hass: HomeAssistant) -> None:
        """Test permission check with permission denied."""
        mock_coordinator = MagicMock()
        mock_coordinator.cluster_name = "Test Cluster"
        mock_coordinator.data = {
            D_USER: {D_ACCESS: {PERM_MANAGEMENT: False, "test_perm": False}}
        }

        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        with pytest.raises(HomeAssistantError, match="Permission 'test_perm' denied"):
            permission_check(hass, "123", "test_perm")

    def test_permission_check_no_coordinator(self, hass: HomeAssistant) -> None:
        """Test permission check with no coordinator available."""
        with pytest.raises(
            HomeAssistantError, match="No permission data available yet"
        ):
            permission_check(hass, "123", "test_perm")

    def test_permission_check_no_data(self, hass: HomeAssistant) -> None:
        """Test permission check with coordinator but no data."""
        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        with pytest.raises(
            HomeAssistantError, match="No permission data available yet"
        ):
            permission_check(hass, "123", "test_perm")


class TestGetDeviceInfo:
    """Test the get_device_info function."""

    def test_get_device_info(self, hass: HomeAssistant) -> None:
        """Test get_device_info function."""
        result = get_device_info("test_cluster")

        assert result["identifiers"] == {("diveracontrol", "test_cluster")}
        assert result["name"] == "test_cluster"
        assert result["manufacturer"] == "Divera GmbH"
        assert result["model"] == "diveracontrol"
        expected_version = f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}"
        assert result["sw_version"] == expected_version
        assert result["entry_type"] == DeviceEntryType.SERVICE
        assert "configuration_url" in result


class TestGetCoordinatorKeyFromDevice:
    """Test the get_coordinator_key_from_device function."""

    def test_get_coordinator_key_from_device_full_coordinator(
        self, hass: HomeAssistant
    ) -> None:
        """Test getting full coordinator when no key specified."""
        mock_device = MagicMock()
        mock_device.config_entries = {"entry1"}

        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN
        mock_entry.runtime_data = MagicMock()

        with (
            patch(
                "custom_components.diveracontrol.utils.dr.async_get"
            ) as mock_device_registry,
            patch.object(
                hass.config_entries, "async_get_entry", return_value=mock_entry
            ),
        ):
            mock_device_registry.return_value.async_get.return_value = mock_device

            result = get_coordinator_key_from_device(hass, "device1")

            assert result == mock_entry.runtime_data

    def test_get_coordinator_key_from_device_specific_key(
        self, hass: HomeAssistant
    ) -> None:
        """Test getting specific key from coordinator."""
        mock_device = MagicMock()
        mock_device.config_entries = {"entry1"}

        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN
        mock_coordinator = MagicMock()
        mock_coordinator.some_key = "test_value"
        mock_entry.runtime_data = mock_coordinator

        with (
            patch(
                "custom_components.diveracontrol.utils.dr.async_get"
            ) as mock_device_registry,
            patch.object(
                hass.config_entries, "async_get_entry", return_value=mock_entry
            ),
        ):
            mock_device_registry.return_value.async_get.return_value = mock_device

            result = get_coordinator_key_from_device(hass, "device1", "some_key")

            assert result == "test_value"

    def test_get_coordinator_key_from_device_key_not_found(
        self, hass: HomeAssistant
    ) -> None:
        """Test error when key not found in coordinator."""
        mock_device = MagicMock()
        mock_device.config_entries = {"entry1"}

        mock_entry = MagicMock()
        mock_entry.domain = DOMAIN
        mock_coordinator = MagicMock()
        mock_entry.runtime_data = mock_coordinator

        with (
            patch(
                "custom_components.diveracontrol.utils.dr.async_get"
            ) as mock_device_registry,
            patch.object(
                hass.config_entries, "async_get_entry", return_value=mock_entry
            ),
        ):
            mock_device_registry.return_value.async_get.return_value = mock_device

            # This should not raise an exception - it returns the coordinator
            result = get_coordinator_key_from_device(hass, "device1")
            assert result == mock_coordinator

    def test_get_coordinator_key_from_device_not_found(
        self, hass: HomeAssistant
    ) -> None:
        """Test error when device not found."""
        with patch(
            "custom_components.diveracontrol.utils.dr.async_get"
        ) as mock_device_registry:
            mock_device_registry.return_value.async_get.return_value = None

            with pytest.raises(HomeAssistantError, match="Device not found"):
                get_coordinator_key_from_device(hass, "device1")

    def test_get_coordinator_key_from_device_no_config_entries(
        self, hass: HomeAssistant
    ) -> None:
        """Test error when device has no config entries."""
        mock_device = MagicMock()
        mock_device.config_entries = set()  # Empty set

        with patch(
            "custom_components.diveracontrol.utils.dr.async_get"
        ) as mock_device_registry:
            mock_device_registry.return_value.async_get.return_value = mock_device

            with pytest.raises(HomeAssistantError, match="Device not found: device1"):
                get_coordinator_key_from_device(hass, "device1")

    def test_get_coordinator_key_from_device_wrong_domain(
        self, hass: HomeAssistant
    ) -> None:
        """Test error when config entry has wrong domain."""
        mock_device = MagicMock()
        mock_device.config_entries = {"entry1"}

        mock_entry = MagicMock()
        mock_entry.domain = "wrong_domain"

        with (
            patch(
                "custom_components.diveracontrol.utils.dr.async_get"
            ) as mock_device_registry,
            patch.object(
                hass.config_entries, "async_get_entry", return_value=mock_entry
            ),
        ):
            mock_device_registry.return_value.async_get.return_value = mock_device

            with pytest.raises(HomeAssistantError, match="Invalid config entry"):
                get_coordinator_key_from_device(hass, "device1")


class TestHandleEntity:
    """Test the handle_entity function."""

    @pytest.fixture
    def mock_coordinator(self) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.data = {
            D_ALARM: {
                "items": {
                    "alarm1": {
                        "closed": False,
                        "title": "Test Alarm",
                        "status": "old_status",
                    },
                    "alarm2": {"closed": True, "title": "Closed Alarm"},
                }
            },
            D_CLUSTER: {
                D_VEHICLE: {
                    "vehicle1": {
                        "name": "Test Vehicle",
                        "fms": 1,
                        "properties": {"old": "value"},
                    },
                    "vehicle2": {
                        "name": "Other Vehicle",
                        "crew": [{"id": 1}, {"id": 2}],
                    },
                }
            },
        }
        return coordinator

    async def test_handle_entity_put_alarm(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity with put_alarm service."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {"alarm_id": "alarm1", "status": "new_status", "title": "Updated Alarm"}

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(hass, data, "put_alarm", "123", "alarm1")

            # Check that coordinator data was updated
            assert (
                mock_coordinator.data[D_ALARM]["items"]["alarm1"]["status"]
                == "new_status"
            )
            assert (
                mock_coordinator.data[D_ALARM]["items"]["alarm1"]["title"]
                == "Updated Alarm"
            )
            mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_handle_entity_post_close_alarm(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity for post_close_alarm service."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {"alarm_id": "alarm1", "closed": True}

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(hass, data, "post_close_alarm", "123", "alarm1")

            assert mock_coordinator.data[D_ALARM]["items"]["alarm1"]["closed"] is True
            mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_handle_entity_alarm_not_found(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity when alarm not found."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {"alarm_id": "nonexistent"}

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(hass, data, "put_alarm", "123", "nonexistent")

            # Should not update coordinator data
            mock_coordinator.async_set_updated_data.assert_not_called()

    async def test_handle_entity_post_vehicle_status(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity with post_vehicle_status service."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {"vehicle_id": "vehicle1", "fms": 3, "name": "Updated Vehicle"}

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(hass, data, "post_vehicle_status", "123", "vehicle1")

            # Check that coordinator data was updated
            assert mock_coordinator.data[D_CLUSTER][D_VEHICLE]["vehicle1"]["fms"] == 3
            assert (
                mock_coordinator.data[D_CLUSTER][D_VEHICLE]["vehicle1"]["name"]
                == "Updated Vehicle"
            )
            mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_handle_entity_post_using_vehicle_property(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity for post_using_vehicle_property service."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {
            "vehicle_id": "vehicle1",
            "properties": {"new_prop": "new_value", "old": "updated"},
        }

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(
                hass, data, "post_using_vehicle_property", "123", "vehicle1"
            )

            properties = mock_coordinator.data[D_CLUSTER][D_VEHICLE]["vehicle1"][
                "properties"
            ]
            assert properties["new_prop"] == "new_value"
            assert properties["old"] == "updated"  # Should be updated
            mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_handle_entity_post_using_vehicle_crew_add(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity for post_using_vehicle_crew service with add mode."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {"vehicle_id": "vehicle2", "mode": "add", "crew": [3, 4]}

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(
                hass, data, "post_using_vehicle_crew", "123", "vehicle2"
            )

            crew = mock_coordinator.data[D_CLUSTER][D_VEHICLE]["vehicle2"]["crew"]
            crew_ids = [member["id"] for member in crew]
            assert set(crew_ids) == {1, 2, 3, 4}  # Original + added
            mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_handle_entity_post_using_vehicle_crew_remove(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity for post_using_vehicle_crew service with remove mode."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {"vehicle_id": "vehicle2", "mode": "remove", "crew": [1]}

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(
                hass, data, "post_using_vehicle_crew", "123", "vehicle2"
            )

            crew = mock_coordinator.data[D_CLUSTER][D_VEHICLE]["vehicle2"]["crew"]
            crew_ids = [member["id"] for member in crew]
            assert crew_ids == [2]  # Only ID 2 should remain
            mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_handle_entity_post_using_vehicle_crew_reset(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity for post_using_vehicle_crew service with reset mode."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        data = {"vehicle_id": "vehicle2", "mode": "reset"}

        with patch(
            "custom_components.diveracontrol.utils.get_translation", return_value="test"
        ):
            await handle_entity(
                hass, data, "post_using_vehicle_crew", "123", "vehicle2"
            )

            crew = mock_coordinator.data[D_CLUSTER][D_VEHICLE]["vehicle2"]["crew"]
            assert crew == []  # Should be empty
            mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_handle_entity_unknown_service(
        self, hass: HomeAssistant, mock_coordinator: MagicMock
    ) -> None:
        """Test handle_entity with unknown service."""
        hass.data[DOMAIN] = {"123": {D_COORDINATOR: mock_coordinator}}

        with patch(
            "custom_components.diveracontrol.utils.get_translation",
            return_value="Unknown service",
        ):
            with pytest.raises(HomeAssistantError, match="Unknown service"):
                await handle_entity(hass, {}, "unknown_service", "123", "entity1")

    async def test_handle_entity_no_coordinator(self, hass: HomeAssistant) -> None:
        """Test handle_entity with no coordinator found."""
        with patch(
            "custom_components.diveracontrol.utils.get_translation",
            return_value="Coordinator not found",
        ):
            with pytest.raises(HomeAssistantError, match="Coordinator not found"):
                await handle_entity(hass, {}, "put_alarm", "123", "alarm1")


class TestSetUpdateInterval:
    """Test the set_update_interval function."""

    def test_set_update_interval_with_open_alarms(self) -> None:
        """Test set_update_interval when there are open alarms."""
        cluster_data = {
            D_ALARM: {
                "items": {
                    "alarm1": {"closed": False},
                    "alarm2": {"closed": True},
                    "alarm3": {"closed": False},
                }
            }
        }
        interval_data = {
            D_UPDATE_INTERVAL_ALARM: timedelta(seconds=30),
            D_UPDATE_INTERVAL_DATA: timedelta(minutes=5),
        }

        result = set_update_interval(cluster_data, interval_data, None)

        assert result == timedelta(seconds=30)  # Should use alarm interval
        assert cluster_data[D_ALARM][D_OPEN_ALARMS] == 2  # Two open alarms

    def test_set_update_interval_no_open_alarms(self) -> None:
        """Test set_update_interval when there are no open alarms."""
        cluster_data = {
            D_ALARM: {"items": {"alarm1": {"closed": True}, "alarm2": {"closed": True}}}
        }
        interval_data = {
            D_UPDATE_INTERVAL_ALARM: timedelta(seconds=30),
            D_UPDATE_INTERVAL_DATA: timedelta(minutes=5),
        }

        result = set_update_interval(cluster_data, interval_data, None)

        assert result == timedelta(minutes=5)  # Should use data interval
        assert cluster_data[D_ALARM][D_OPEN_ALARMS] == 0  # No open alarms

    def test_set_update_interval_empty_alarm_items(self) -> None:
        """Test set_update_interval with empty alarm items."""
        cluster_data = {D_ALARM: {"items": {}}}
        interval_data = {
            D_UPDATE_INTERVAL_ALARM: timedelta(seconds=30),
            D_UPDATE_INTERVAL_DATA: timedelta(minutes=5),
        }

        result = set_update_interval(cluster_data, interval_data, None)

        assert result == timedelta(minutes=5)
        assert cluster_data[D_ALARM][D_OPEN_ALARMS] == 0

    def test_set_update_interval_no_alarm_data(self) -> None:
        """Test set_update_interval with no alarm data."""
        cluster_data = {}
        interval_data = {
            D_UPDATE_INTERVAL_ALARM: timedelta(seconds=30),
            D_UPDATE_INTERVAL_DATA: timedelta(minutes=5),
        }

        result = set_update_interval(cluster_data, interval_data, None)

        assert result == timedelta(minutes=5)
        assert cluster_data[D_ALARM][D_OPEN_ALARMS] == 0


class TestGetTranslation:
    """Test the get_translation function."""

    async def test_get_translation_simple(self, hass: HomeAssistant) -> None:
        """Test get_translation with simple translation."""
        translations = {
            "component.diveracontrol.exceptions.test_key.message": "Test message"
        }

        with patch(
            "custom_components.diveracontrol.utils.async_get_translations",
            return_value=translations,
        ):
            result = await get_translation(hass, "exceptions", "test_key.message")

            assert result == "Test message"

    async def test_get_translation_with_placeholders(self, hass: HomeAssistant) -> None:
        """Test get_translation with placeholders."""
        translations = {
            "component.diveracontrol.exceptions.test_key.message": "Error for {item}: {details}"
        }

        with patch(
            "custom_components.diveracontrol.utils.async_get_translations",
            return_value=translations,
        ):
            result = await get_translation(
                hass,
                "exceptions",
                "test_key.message",
                {"item": "device1", "details": "not found"},
            )

            assert result == "Error for device1: not found"

    async def test_get_translation_missing_key(self, hass: HomeAssistant) -> None:
        """Test get_translation with missing translation key."""
        translations = {}

        with patch(
            "custom_components.diveracontrol.utils.async_get_translations",
            return_value=translations,
        ):
            result = await get_translation(hass, "exceptions", "missing_key.message")

            assert result == "component.diveracontrol.exceptions.missing_key.message"

    async def test_get_translation_missing_placeholder(
        self, hass: HomeAssistant
    ) -> None:
        """Test get_translation with missing placeholder."""
        with patch(
            "custom_components.diveracontrol.utils.async_get_translations",
            return_value={},
        ):
            result = await get_translation(
                hass, "test", "missing_key", {"item": "device1", "missing": None}
            )

            # Should return the translation key since translation not found
            assert result == "component.diveracontrol.test.missing_key"
