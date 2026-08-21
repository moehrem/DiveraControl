"""Tests for DiveraControl __init__.py module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from custom_components.diveracontrol import (
    DOMAIN,
    PLATFORMS,
    VERSION,
    MINOR_VERSION,
    PATCH_VERSION,
    async_migrate_entry,
    async_remove_config_entry_device,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.diveracontrol.const import (
    D_ACCESSKEY,
    D_BASE_API_URL,
    D_CLUSTER_ID,
    D_CLUSTER_NAME,
    D_COORDINATOR,
    D_INTEGRATION_VERSION,
    D_RELATIONS_KEY,
    D_UCR_ID,
    D_UPDATE_INTERVAL_ALARM,
    D_UPDATE_INTERVAL_DATA,
    D_USE_WEBHOOKS,
    D_USERNAME,
)
from custom_components.diveracontrol.coordinator import DiveraCoordinator


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {
        D_CLUSTER_ID: "test_cluster_id",
        D_CLUSTER_NAME: "Test Cluster",
        D_BASE_API_URL: "https://api.test.com",
        D_UPDATE_INTERVAL_DATA: 60,
        D_UPDATE_INTERVAL_ALARM: 30,
        D_INTEGRATION_VERSION: f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
        D_RELATIONS_KEY: {
            "ucr1": {
                D_ACCESSKEY: "test_accesskey_1",
                D_USERNAME: "user1",
            },
            "ucr2": {
                D_ACCESSKEY: "test_accesskey_2",
                D_USERNAME: "user2",
            },
        },
    }
    entry.entry_id = "test_entry_id"
    entry.version = VERSION
    entry.minor_version = MINOR_VERSION
    entry.title = "Test Cluster"
    return entry


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_reload = AsyncMock(return_value=None)
    return hass


class TestPlatforms:
    """Test PLATFORMS constant."""

    def test_platforms_defined(self) -> None:
        """Test that all platforms are defined."""
        assert Platform.CALENDAR in PLATFORMS
        assert Platform.DEVICE_TRACKER in PLATFORMS
        assert Platform.SELECT in PLATFORMS
        assert Platform.SENSOR in PLATFORMS
        assert len(PLATFORMS) == 4


class TestAsyncSetup:
    """Test async_setup function."""

    @pytest.mark.asyncio
    async def test_async_setup_success(self, hass: HomeAssistant) -> None:
        """Test successful async_setup."""
        with (
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ) as mock_log_setup,
            patch(
                "custom_components.diveracontrol.async_register_services"
            ) as mock_register_services,
        ):
            result = await async_setup(hass, {})
            assert result is True
            mock_log_setup.assert_called_once_with(hass)
            mock_register_services.assert_called_once_with(hass, DOMAIN)


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test successful async_setup_entry with valid config."""
        mock_coordinator = AsyncMock(spec=DiveraCoordinator)
        mock_coordinator._async_setup = AsyncMock(return_value=None)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=(
                    "test_cluster_id",
                    {},
                    {"ucr1": mock_config_entry.data[D_RELATIONS_KEY]["ucr1"]},
                ),
            ),
            patch(
                "custom_components.diveracontrol.DiveraCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ) as mock_forward,
        ):
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is True
            mock_forward.assert_called_once_with(mock_config_entry, PLATFORMS)
            assert DOMAIN in hass.data
            assert "test_cluster_id" in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_async_setup_entry_no_coordinators(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test async_setup_entry fails when no coordinators can be created."""
        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=("test_cluster_id", {}, {}),
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
        ):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_invalid_relation_data(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test async_setup_entry with invalid relation data type - skips invalid entries."""
        mock_config_entry.data[D_RELATIONS_KEY] = {
            "ucr1": "not_a_dict",
            "ucr2": {D_ACCESSKEY: "valid_key", D_USERNAME: "valid_user"},
        }

        mock_coordinator = AsyncMock(spec=DiveraCoordinator)
        mock_coordinator._async_setup = AsyncMock(return_value=None)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=(
                    "test_cluster_id",
                    {},
                    mock_config_entry.data[D_RELATIONS_KEY],
                ),
            ),
            patch(
                "custom_components.diveracontrol.DiveraCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ),
        ):
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_async_setup_entry_missing_username(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test async_setup_entry with missing username in relation data."""
        mock_config_entry.data[D_RELATIONS_KEY] = {
            "ucr1": {D_ACCESSKEY: "test_accesskey_1"}
        }

        mock_coordinator = AsyncMock(spec=DiveraCoordinator)
        mock_coordinator._async_setup = AsyncMock(return_value=None)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=(
                    "test_cluster_id",
                    {},
                    mock_config_entry.data[D_RELATIONS_KEY],
                ),
            ),
            patch(
                "custom_components.diveracontrol.DiveraCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ),
        ):
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is True

    @pytest.mark.asyncio
    async def test_async_setup_entry_coordinator_setup_failure(
        self, hass: HomeAssistant
    ) -> None:
        """Test async_setup_entry when all coordinators fail setup."""
        mock_config_entry = MagicMock(spec=ConfigEntry)
        mock_config_entry.data = {
            D_CLUSTER_ID: "test_cluster_id",
            D_CLUSTER_NAME: "Test Cluster",
            D_BASE_API_URL: "https://api.test.com",
            D_UPDATE_INTERVAL_DATA: 60,
            D_UPDATE_INTERVAL_ALARM: 30,
            D_RELATIONS_KEY: {
                "ucr1": {D_ACCESSKEY: "test_key", D_USERNAME: "user1"},
            },
        }
        mock_config_entry.entry_id = "test_entry_id"

        mock_coordinator = AsyncMock(spec=DiveraCoordinator)
        mock_coordinator._async_setup = AsyncMock(
            side_effect=ConfigEntryNotReady("Not ready")
        )

        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=(
                    "test_cluster_id",
                    {},
                    mock_config_entry.data[D_RELATIONS_KEY],
                ),
            ),
            patch(
                "custom_components.diveracontrol.DiveraCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
        ):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_all_coordinators_fail(
        self, hass: HomeAssistant
    ) -> None:
        """Test async_setup_entry when all coordinators fail setup - same as above."""
        mock_config_entry = MagicMock(spec=ConfigEntry)
        mock_config_entry.data = {
            D_CLUSTER_ID: "test_cluster_id",
            D_CLUSTER_NAME: "Test Cluster",
            D_BASE_API_URL: "https://api.test.com",
            D_UPDATE_INTERVAL_DATA: 60,
            D_UPDATE_INTERVAL_ALARM: 30,
            D_RELATIONS_KEY: {
                "ucr1": {D_ACCESSKEY: "test_key", D_USERNAME: "user1"},
            },
        }
        mock_config_entry.entry_id = "test_entry_id"

        mock_coordinator = AsyncMock(spec=DiveraCoordinator)
        mock_coordinator._async_setup = AsyncMock(
            side_effect=ConfigEntryNotReady("Not ready")
        )

        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=(
                    "test_cluster_id",
                    {},
                    mock_config_entry.data[D_RELATIONS_KEY],
                ),
            ),
            patch(
                "custom_components.diveracontrol.DiveraCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
        ):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_refresh_failure(self, hass: HomeAssistant) -> None:
        """Test async_setup_entry when all coordinators fail refresh."""
        mock_config_entry = MagicMock(spec=ConfigEntry)
        mock_config_entry.data = {
            D_CLUSTER_ID: "test_cluster_id",
            D_CLUSTER_NAME: "Test Cluster",
            D_BASE_API_URL: "https://api.test.com",
            D_UPDATE_INTERVAL_DATA: 60,
            D_UPDATE_INTERVAL_ALARM: 30,
            D_RELATIONS_KEY: {
                "ucr1": {D_ACCESSKEY: "test_key", D_USERNAME: "user1"},
            },
        }
        mock_config_entry.entry_id = "test_entry_id"

        mock_coordinator = AsyncMock(spec=DiveraCoordinator)
        mock_coordinator._async_setup = AsyncMock(return_value=None)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=ConfigEntryAuthFailed("Auth failed")
        )

        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=(
                    "test_cluster_id",
                    {},
                    mock_config_entry.data[D_RELATIONS_KEY],
                ),
            ),
            patch(
                "custom_components.diveracontrol.DiveraCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
        ):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_empty_cluster_name(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test async_setup_entry with empty cluster name."""
        mock_config_entry.data[D_CLUSTER_NAME] = ""

        mock_coordinator = AsyncMock(spec=DiveraCoordinator)
        mock_coordinator._async_setup = AsyncMock(return_value=None)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.diveracontrol.get_cluster_coordinators_ucrs_from_config_hass",
                return_value=(
                    "test_cluster_id",
                    {},
                    mock_config_entry.data[D_RELATIONS_KEY],
                ),
            ),
            patch(
                "custom_components.diveracontrol.DiveraCoordinator",
                return_value=mock_coordinator,
            ),
            patch(
                "custom_components.diveracontrol.async_setup_diveracontrol_log_handler"
            ),
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ),
        ):
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is True


class TestAsyncUnloadEntry:
    """Test async_unload_entry function."""

    @pytest.fixture
    def mock_hass_unload(self) -> HomeAssistant:
        """Create a mock Home Assistant instance for unload tests."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.config_entries._entries = {}
        return hass

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(
        self, mock_hass_unload: HomeAssistant
    ) -> None:
        """Test successful async_unload_entry."""
        cluster_id = "test_cluster_id"
        mock_hass_unload.data = {
            DOMAIN: {
                cluster_id: {D_COORDINATOR: {"ucr1": MagicMock(), "ucr2": MagicMock()}}
            }
        }

        mock_config_entry = MagicMock(spec=ConfigEntry)
        mock_config_entry.data = {
            D_CLUSTER_ID: cluster_id,
            D_CLUSTER_NAME: "Test Cluster",
        }

        with patch.object(
            mock_hass_unload.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
        ) as mock_unload_platforms:
            mock_unload_platforms.return_value = True

            result = await async_unload_entry(mock_hass_unload, mock_config_entry)
            assert result is True
            assert cluster_id not in mock_hass_unload.data.get(DOMAIN, {}), (
                f"Expected {cluster_id} not in {mock_hass_unload.data.get(DOMAIN, {})}"
            )
            mock_unload_platforms.assert_called_once_with(mock_config_entry, PLATFORMS)

    @pytest.mark.asyncio
    async def test_async_unload_entry_platforms_failure(
        self, mock_hass_unload: HomeAssistant
    ) -> None:
        """Test async_unload_entry when unloading platforms fails."""
        cluster_id = "test_cluster_id"
        mock_hass_unload.data = {DOMAIN: {cluster_id: {D_COORDINATOR: {}}}}

        mock_config_entry = MagicMock(spec=ConfigEntry)
        mock_config_entry.data = {
            D_CLUSTER_ID: cluster_id,
            D_CLUSTER_NAME: "Test Cluster",
        }

        with patch.object(
            mock_hass_unload.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
        ) as mock_unload_platforms:
            mock_unload_platforms.return_value = False

            result = await async_unload_entry(mock_hass_unload, mock_config_entry)
            assert result is False
            assert cluster_id in mock_hass_unload.data.get(DOMAIN, {}), (
                f"Expected {cluster_id} in {mock_hass_unload.data.get(DOMAIN, {})}"
            )

    @pytest.mark.asyncio
    async def test_async_unload_entry_last_cluster(
        self, mock_hass_unload: HomeAssistant
    ) -> None:
        """Test async_unload_entry when removing last cluster."""
        cluster_id = "test_cluster_id"
        mock_hass_unload.data = {DOMAIN: {cluster_id: {D_COORDINATOR: {}}}}

        mock_config_entry = MagicMock(spec=ConfigEntry)
        mock_config_entry.data = {
            D_CLUSTER_ID: cluster_id,
            D_CLUSTER_NAME: "Test Cluster",
        }

        with (
            patch.object(
                mock_hass_unload.config_entries,
                "async_unload_platforms",
                new_callable=AsyncMock,
            ) as mock_unload_platforms,
            patch(
                "custom_components.diveracontrol.async_remove_diveracontrol_log_handler"
            ) as mock_remove_log_handler,
        ):
            mock_unload_platforms.return_value = True

            result = await async_unload_entry(mock_hass_unload, mock_config_entry)
            assert result is True
            assert DOMAIN not in mock_hass_unload.data, (
                f"Expected DOMAIN not in {mock_hass_unload.data}"
            )
            mock_remove_log_handler.assert_called_once_with(mock_hass_unload)


class TestAsyncRemoveConfigEntryDevice:
    """Test async_remove_config_entry_device function."""

    @pytest.mark.asyncio
    async def test_async_remove_config_entry_device_success(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test successful device removal."""
        device_entry = MagicMock(spec=dr.DeviceEntry)
        device_entry.identifiers = [(DOMAIN, "ucr1")]

        with (
            patch.object(
                hass.config_entries, "async_update_entry", return_value=None
            ) as mock_update_entry,
            patch.object(
                hass.config_entries, "async_reload", new_callable=AsyncMock
            ) as mock_reload,
        ):
            result = await async_remove_config_entry_device(
                hass, mock_config_entry, device_entry
            )
            assert result is True
            mock_update_entry.assert_called_once()
            mock_reload.assert_called_once_with("test_entry_id")

    @pytest.mark.asyncio
    async def test_async_remove_config_entry_device_no_domain_identifier(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test device removal when device has no DOMAIN identifier."""
        device_entry = MagicMock(spec=dr.DeviceEntry)
        device_entry.identifiers = [("other_domain", "device1")]

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, device_entry
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_async_remove_config_entry_device_cluster_id_match(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test device removal when ucr_id matches cluster_id."""
        device_entry = MagicMock(spec=dr.DeviceEntry)
        device_entry.identifiers = [(DOMAIN, "test_cluster_id")]

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, device_entry
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_async_remove_config_entry_device_ucr_not_in_relations(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test device removal when ucr_id is not in relations."""
        device_entry = MagicMock(spec=dr.DeviceEntry)
        device_entry.identifiers = [(DOMAIN, "unknown_ucr")]

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, device_entry
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_async_remove_config_entry_device_invalid_relations_type(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test device removal when relations is not a dict."""
        device_entry = MagicMock(spec=dr.DeviceEntry)
        device_entry.identifiers = [(DOMAIN, "ucr1")]
        mock_config_entry.data[D_RELATIONS_KEY] = "not_a_dict"

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, device_entry
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_async_remove_config_entry_device_last_relation(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test device removal when it is the last relation."""
        device_entry = MagicMock(spec=dr.DeviceEntry)
        device_entry.identifiers = [(DOMAIN, "ucr1")]
        mock_config_entry.data[D_RELATIONS_KEY] = {
            "ucr1": mock_config_entry.data[D_RELATIONS_KEY]["ucr1"]
        }

        result = await async_remove_config_entry_device(
            hass, mock_config_entry, device_entry
        )
        assert result is False


class TestRemoveOldEntityEntries:
    """Test _remove_old_entity_entries function."""

    def test_remove_old_entity_entries_success(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test successful removal of old entity entries."""
        from custom_components.diveracontrol import _remove_old_entity_entries

        mock_entity = MagicMock()
        mock_entity.entity_id = "sensor.test_entity"
        mock_entity.unique_id = "test_unique_id"
        mock_entity.config_entry_id = mock_config_entry.entry_id

        mock_entity_registry = MagicMock()
        mock_entity_registry.entities = {"sensor.test_entity": mock_entity}
        mock_entity_registry.async_remove = MagicMock()

        with patch(
            "custom_components.diveracontrol.er.async_get",
            return_value=mock_entity_registry,
        ):
            _remove_old_entity_entries(hass, mock_config_entry)
            mock_entity_registry.async_remove.assert_called_once_with(
                "sensor.test_entity"
            )

    def test_remove_old_entity_entries_exception(
        self, hass: HomeAssistant, mock_config_entry: ConfigEntry
    ) -> None:
        """Test _remove_old_entity_entries with exception."""
        from custom_components.diveracontrol import _remove_old_entity_entries

        with patch(
            "custom_components.diveracontrol.er.async_get",
            side_effect=Exception("Test error"),
        ):
            _remove_old_entity_entries(hass, mock_config_entry)


# class TestMigrations:
#     """Test migration functions."""

#     @pytest.mark.asyncio
#     async def test_async_migrate_entry_no_migration_needed(
#         self, hass: HomeAssistant, mock_config_entry: ConfigEntry
#     ) -> None:
#         """Test migration when no migration is needed."""
#         result = await async_migrate_entry(hass, mock_config_entry)
#         assert result is True

#     @pytest.mark.asyncio
#     async def test_async_migrate_entry_current_version(
#         self, hass: HomeAssistant
#     ) -> None:
#         """Test migration when config entry is already at current version."""
#         mock_config_entry = MagicMock(spec=ConfigEntry)
#         mock_config_entry.data = {
#             D_CLUSTER_ID: "test_cluster",
#             D_CLUSTER_NAME: "Test Cluster",
#             D_INTEGRATION_VERSION: f"{VERSION}.{MINOR_VERSION}.{PATCH_VERSION}",
#         }
#         mock_config_entry.entry_id = "test_entry_id"
#         mock_config_entry.version = VERSION
#         mock_config_entry.minor_version = MINOR_VERSION
#         hass.config_entries._entries = {"test_entry_id": mock_config_entry}
#         hass.config_entries.async_update_entry = MagicMock()

#         result = await async_migrate_entry(hass, mock_config_entry)
#         assert result is True

#     @pytest.mark.asyncio
#     async def test_async_migrate_entry_v2_0_0_success(
#         self, hass: HomeAssistant
#     ) -> None:
#         """Test migration to v2.0.0 with valid API key."""
#         mock_config_entry = MagicMock(spec=ConfigEntry)
#         mock_config_entry.data = {
#             D_CLUSTER_ID: "test_cluster",
#             D_CLUSTER_NAME: "Test Cluster",
#             "api_key": "valid_api_key",
#             D_BASE_API_URL: "https://api.test.com",
#             D_INTEGRATION_VERSION: "1.4.0",
#             D_UCR_ID: "ucr1",
#         }
#         mock_config_entry.entry_id = "test_entry_id"
#         mock_config_entry.version = 1
#         mock_config_entry.minor_version = 4
#         hass.config_entries._entries = {"test_entry_id": mock_config_entry}
#         hass.config_entries.async_update_entry = MagicMock()

#         mock_api_client = AsyncMock()
#         mock_api_client.request_access = AsyncMock(
#             return_value=(
#                 {},
#                 {
#                     "test_cluster": {
#                         D_RELATIONS_KEY: {
#                             "ucr1": {D_ACCESSKEY: "key1", D_USERNAME: "user1"}
#                         },
#                         D_CLUSTER_ID: "test_cluster",
#                         D_CLUSTER_NAME: "Test Cluster",
#                     }
#                 },
#             )
#         )

#         with (
#             patch(
#                 "custom_components.diveracontrol.DiveraAPIClient",
#                 return_value=mock_api_client,
#             ),
#             patch(
#                 "custom_components.diveracontrol.ir.async_create_issue"
#             ) as mock_create_issue,
#             patch("custom_components.diveracontrol.dr.async_get") as mock_dr_get,
#         ):
#             mock_dr = MagicMock()
#             mock_dr.async_clear_config_entry = MagicMock()
#             mock_dr_get.return_value = mock_dr

#             result = await async_migrate_entry(hass, mock_config_entry)
#             assert result is True
#             # The migration calls async_update_entry with the updated data
#             # Check that it was called with D_RELATIONS_KEY in the data
#             call_args = hass.config_entries.async_update_entry.call_args
#             assert call_args is not None
#             assert D_RELATIONS_KEY in call_args[1]["data"]

#     @pytest.mark.asyncio
#     async def test_async_migrate_entry_v2_0_0_api_failure(
#         self, hass: HomeAssistant
#     ) -> None:
#         """Test migration to v2.0.0 when API key validation fails."""
#         mock_config_entry = MagicMock(spec=ConfigEntry)
#         mock_config_entry.data = {
#             D_CLUSTER_ID: "test_cluster",
#             D_CLUSTER_NAME: "Test Cluster",
#             "api_key": "invalid_api_key",
#             D_BASE_API_URL: "https://api.test.com",
#             D_INTEGRATION_VERSION: "1.4.0",
#             D_UCR_ID: "ucr1",
#         }
#         mock_config_entry.entry_id = "test_entry_id"
#         mock_config_entry.version = 1
#         mock_config_entry.minor_version = 4
#         hass.config_entries._entries = {"test_entry_id": mock_config_entry}
#         hass.config_entries.async_update_entry = MagicMock()

#         mock_api_client = AsyncMock()
#         mock_api_client.request_access = AsyncMock(
#             return_value=({"base": "Invalid API key"}, {})
#         )

#         with (
#             patch(
#                 "custom_components.diveracontrol.DiveraAPIClient",
#                 return_value=mock_api_client,
#             ),
#             patch(
#                 "custom_components.diveracontrol.ir.async_create_issue"
#             ) as mock_create_issue,
#         ):
#             result = await async_migrate_entry(hass, mock_config_entry)
#             assert result is False
#             mock_create_issue.assert_called_once()

#     @pytest.mark.asyncio
#     async def test_async_migrate_entry_v2_0_0_no_matching_cluster(
#         self, hass: HomeAssistant
#     ) -> None:
#         """Test migration to v2.0.0 when no matching cluster is found."""
#         mock_config_entry = MagicMock(spec=ConfigEntry)
#         mock_config_entry.data = {
#             D_CLUSTER_ID: "test_cluster",
#             D_CLUSTER_NAME: "Test Cluster",
#             "api_key": "valid_api_key",
#             D_BASE_API_URL: "https://api.test.com",
#             D_INTEGRATION_VERSION: "1.4.0",
#             D_UCR_ID: "unknown_ucr",
#         }
#         mock_config_entry.entry_id = "test_entry_id"
#         mock_config_entry.version = 1
#         mock_config_entry.minor_version = 4
#         hass.config_entries._entries = {"test_entry_id": mock_config_entry}
#         hass.config_entries.async_update_entry = MagicMock()

#         mock_api_client = AsyncMock()
#         mock_api_client.request_access = AsyncMock(
#             return_value=(
#                 {},
#                 {
#                     "test_cluster": {
#                         D_RELATIONS_KEY: {
#                             "ucr1": {D_ACCESSKEY: "key1", D_USERNAME: "user1"}
#                         },
#                         D_CLUSTER_ID: "test_cluster",
#                     }
#                 },
#             )
#         )

#         with (
#             patch(
#                 "custom_components.diveracontrol.DiveraAPIClient",
#                 return_value=mock_api_client,
#             ),
#             patch(
#                 "custom_components.diveracontrol.ir.async_create_issue"
#             ) as mock_create_issue,
#         ):
#             result = await async_migrate_entry(hass, mock_config_entry)
#             assert result is False
#             mock_create_issue.assert_called_once()


# class TestMigrationHelperFunctions:
#     """Test individual migration helper functions."""

#     def test_migrate_to_v1_2_0(self, hass: HomeAssistant) -> None:
#         """Test _migrate_to_v1_2_0 function."""
#         from custom_components.diveracontrol import _migrate_to_v1_2_0

#         mock_config_entry = MagicMock(spec=ConfigEntry)
#         mock_config_entry.data = {D_CLUSTER_ID: "test_cluster", D_CLUSTER_NAME: "Test Cluster"}
#         mock_config_entry.entry_id = "test_entry_id"

#         updated_data = {}
#         with patch(
#             "custom_components.diveracontrol.ir.async_create_issue"
#         ), patch(
#             "custom_components.diveracontrol.er.async_get"
#         ) as mock_er_get:
#             mock_er = MagicMock()
#             mock_er.entities = {}
#             mock_er.async_clear_config_entry = MagicMock()
#             mock_er_get.return_value = mock_er

#             result = _migrate_to_v1_2_0(updated_data, mock_config_entry, hass)
#             assert result[3] is True
#             assert D_INTEGRATION_VERSION in result[0]

#     def test_migrate_to_v1_3_0(self) -> None:
#         """Test _migrate_to_v1_3_0 function."""
#         from custom_components.diveracontrol import _migrate_to_v1_3_0

#         updated_data = {D_CLUSTER_ID: "test_cluster"}
#         result = _migrate_to_v1_3_0(updated_data)
#         assert result[3] is True
#         assert D_BASE_API_URL in result[0]

#     def test_migrate_to_v1_4_0(self) -> None:
#         """Test _migrate_to_v1_4_0 function."""
#         from custom_components.diveracontrol import _migrate_to_v1_4_0

#         updated_data = {D_CLUSTER_ID: "test_cluster"}
#         result = _migrate_to_v1_4_0(updated_data)
#         assert result[3] is True
#         assert D_USE_WEBHOOKS in result[0]
#         assert result[0][D_USE_WEBHOOKS] is False

#     @pytest.mark.asyncio
#     async def test_migrate_to_v2_0_0(self, hass: HomeAssistant) -> None:
#         """Test _migrate_to_v2_0_0 function."""
#         from custom_components.diveracontrol import _migrate_to_v2_0_0

#         mock_config_entry = MagicMock(spec=ConfigEntry)
#         mock_config_entry.data = {
#             D_CLUSTER_ID: "test_cluster",
#             D_CLUSTER_NAME: "Test Cluster",
#             "api_key": "valid_api_key",
#             D_BASE_API_URL: "https://api.test.com",
#             D_UCR_ID: "ucr1",
#             D_UPDATE_INTERVAL_ALARM: 30,
#             D_UPDATE_INTERVAL_DATA: 60,
#         }
#         mock_config_entry.entry_id = "test_entry_id"

#         updated_data = {}
#         mock_api_client = AsyncMock()
#         mock_api_client.request_access = AsyncMock(
#             return_value=(
#                 {},
#                 {
#                     "test_cluster": {
#                         D_RELATIONS_KEY: {"ucr1": {D_ACCESSKEY: "key1", D_USERNAME: "user1"}},
#                         D_CLUSTER_ID: "test_cluster",
#                         D_CLUSTER_NAME: "Test Cluster",
#                     }
#                 },
#             )
#         )

#         with patch(
#             "custom_components.diveracontrol.DiveraAPIClient", return_value=mock_api_client
#         ), patch(
#             "custom_components.diveracontrol.ir.async_create_issue"
#         ):
#             result = await _migrate_to_v2_0_0(hass, mock_config_entry, updated_data)
#             assert result is not None
#             assert D_RELATIONS_KEY in result[0]
