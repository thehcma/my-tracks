"""Tests for the MQTT OwnTracks plugin."""

import json
import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.test import TestCase
from hamcrest import (assert_that, equal_to, has_entries, has_length, is_,
                      is_not, none)

from my_tracks.models import Location
from my_tracks.mqtt.plugin import OwnTracksPlugin, save_location_to_db

# Allow sync DB access in async tests for testing purposes
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class TestSaveLocationToDb(TestCase):
    """Tests for save_location_to_db function."""

    def test_save_valid_location(self) -> None:
        """Should save location and return serialized data."""
        location_data = {
            "device": "testuser/phone",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "timestamp": datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            "tracker_id": "PH",
            "accuracy": 10,
            "altitude": 50,
            "velocity": 5,
            "battery": 85,
        }

        result = save_location_to_db(location_data)

        assert_that(result, is_not(none()))
        assert result is not None
        assert_that(result, has_entries({
            "device_id_display": "testuser/phone",
            "latitude": "51.5074000000",
            "longitude": "-0.1278000000",
        }))

        # Verify saved to database
        location = Location.objects.get(id=result["id"])
        assert_that(location.device.device_id, equal_to("testuser/phone"))
        assert_that(float(location.latitude), equal_to(51.5074))
        assert_that(float(location.longitude), equal_to(-0.1278))
        assert_that(location.tracker_id, equal_to("PH"))
        assert_that(location.battery_level, equal_to(85))

    def test_save_location_minimal(self) -> None:
        """Should save location with only required fields."""
        location_data = {
            "device": "user/device",
            "latitude": 40.7128,
            "longitude": -74.006,
            "timestamp": datetime(2024, 6, 15, 9, 30, 0, tzinfo=UTC),
        }

        result = save_location_to_db(location_data)

        assert_that(result, is_not(none()))
        assert result is not None
        assert_that(result["device_id_display"], equal_to("user/device"))

    def test_save_location_exception(self) -> None:
        """Should return None on database error."""
        location_data = {
            "device": "user/device",
            # Missing required latitude
            "longitude": -74.006,
            "timestamp": datetime.now(tz=UTC),
        }

        result = save_location_to_db(location_data)
        assert_that(result, is_(none()))


@pytest.fixture
def mock_broker_context() -> MagicMock:
    """Create a mock BrokerContext for testing."""
    context = MagicMock()
    context.config = {}
    return context


class TestOwnTracksPluginInit:
    """Tests for OwnTracksPlugin initialization."""

    def test_plugin_initializes(self, mock_broker_context: MagicMock) -> None:
        """Should initialize plugin with message handler."""
        plugin = OwnTracksPlugin(mock_broker_context)

        assert_that(plugin._handler, is_not(none()))
        assert_that(plugin._handler._location_callbacks, has_length(1))
        assert_that(plugin._handler._lwt_callbacks, has_length(1))
        assert_that(plugin._handler._transition_callbacks, has_length(1))


@pytest.mark.django_db
class TestOwnTracksPluginMessageHandling:
    """Tests for OwnTracksPlugin message handling."""

    @pytest.fixture
    def plugin(self, mock_broker_context: MagicMock) -> OwnTracksPlugin:
        """Create plugin instance for testing."""
        return OwnTracksPlugin(mock_broker_context)

    @pytest.fixture
    def mock_message(self) -> MagicMock:
        """Create a mock ApplicationMessage."""
        message = MagicMock()
        message.topic = "owntracks/testuser/phone"
        message.data = json.dumps({
            "_type": "location",
            "lat": 51.5,
            "lon": -0.1,
            "tst": 1704067200,
            "tid": "TS",
            "acc": 5,
        }).encode()
        return message

    @pytest.mark.asyncio
    async def test_ignores_non_owntracks_topic(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should ignore messages on non-owntracks topics."""
        message = MagicMock()
        message.topic = "home/sensors/temp"
        message.data = b'{"value": 22.5}'

        initial_count = Location.objects.count()

        await plugin.on_broker_message_received(
            client_id="test-client",
            message=message,
        )

        assert_that(Location.objects.count(), equal_to(initial_count))

    @pytest.mark.asyncio
    async def test_processes_location_message(
        self,
        plugin: OwnTracksPlugin,
        mock_message: MagicMock,
    ) -> None:
        """Should process location message and save to database."""
        initial_count = Location.objects.count()

        # Mock the WebSocket broadcast to avoid channel layer issues
        with patch.object(plugin, "_broadcast_location", new_callable=AsyncMock):
            await plugin.on_broker_message_received(
                client_id="test-client",
                message=mock_message,
            )

        # Should have saved one location
        assert_that(Location.objects.count(), equal_to(initial_count + 1))

        # Verify the saved location
        location = Location.objects.latest("id")
        assert_that(location.device.device_id, equal_to("testuser/phone"))
        assert_that(float(location.latitude), equal_to(51.5))
        assert_that(float(location.longitude), equal_to(-0.1))
        assert_that(location.tracker_id, equal_to("TS"))

    @pytest.mark.asyncio
    async def test_broadcasts_location_via_websocket(
        self,
        plugin: OwnTracksPlugin,
        mock_message: MagicMock,
    ) -> None:
        """Should broadcast location to WebSocket clients."""
        broadcast_mock = AsyncMock()

        with patch.object(plugin, "_broadcast_location", broadcast_mock):
            await plugin.on_broker_message_received(
                client_id="test-client",
                message=mock_message,
            )

        # Verify broadcast was called
        broadcast_mock.assert_called_once()
        call_args = broadcast_mock.call_args[0][0]
        assert_that(call_args, has_entries(
            device_id_display="testuser/phone",
        ))

    @pytest.mark.asyncio
    async def test_handles_lwt_message(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should handle LWT (offline) messages."""
        message = MagicMock()
        message.topic = "owntracks/user/device"
        message.data = json.dumps({
            "_type": "lwt",
            "tst": 1704067200,
        }).encode()

        # Should not raise - LWT handling is logged but doesn't save to DB yet
        await plugin.on_broker_message_received(
            client_id="test-client",
            message=message,
        )

    @pytest.mark.asyncio
    async def test_handles_transition_message(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should handle transition messages."""
        message = MagicMock()
        message.topic = "owntracks/user/device"
        message.data = json.dumps({
            "_type": "transition",
            "event": "enter",
            "desc": "Home",
            "tst": 1704067200,
            "lat": 51.5,
            "lon": -0.1,
        }).encode()

        # Should not raise - transition handling is logged but doesn't save to DB yet
        await plugin.on_broker_message_received(
            client_id="test-client",
            message=message,
        )

    @pytest.mark.asyncio
    async def test_handles_bytearray_payload(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should handle bytearray payload (in addition to bytes)."""
        message = MagicMock()
        message.topic = "owntracks/user/device"
        # Use bytearray instead of bytes
        message.data = bytearray(json.dumps({
            "_type": "location",
            "lat": 40.0,
            "lon": -74.0,
            "tst": 1704067200,
        }).encode())

        with patch.object(plugin, "_broadcast_location", new_callable=AsyncMock):
            await plugin.on_broker_message_received(
                client_id="test-client",
                message=message,
            )

        # Should have saved the location
        location = Location.objects.latest("id")
        assert_that(float(location.latitude), equal_to(40.0))

    @pytest.mark.asyncio
    async def test_handles_invalid_json_gracefully(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should handle invalid JSON without crashing."""
        message = MagicMock()
        message.topic = "owntracks/user/device"
        message.data = b"not valid json"

        initial_count = Location.objects.count()

        # Should not raise
        await plugin.on_broker_message_received(
            client_id="test-client",
            message=message,
        )

        # No location should be saved
        assert_that(Location.objects.count(), equal_to(initial_count))


@pytest.mark.django_db
class TestBroadcastLocation:
    """Tests for WebSocket broadcast functionality."""

    @pytest.fixture
    def plugin(self, mock_broker_context: MagicMock) -> OwnTracksPlugin:
        """Create plugin instance for testing."""
        return OwnTracksPlugin(mock_broker_context)

    @pytest.mark.asyncio
    async def test_broadcast_with_channel_layer(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should broadcast to channel layer when available."""
        mock_layer = AsyncMock()
        mock_layer.group_send = AsyncMock()

        location_data = {
            "id": 123,
            "device_id": "user/device",
            "latitude": 51.5,
            "longitude": -0.1,
        }

        with patch("my_tracks.mqtt.plugin.get_channel_layer_lazy", return_value=mock_layer):
            await plugin._broadcast_location(location_data)

        mock_layer.group_send.assert_called_once()
        call_args = mock_layer.group_send.call_args
        assert_that(call_args[0][0], equal_to("locations"))
        assert_that(call_args[0][1], has_entries(
            type="location_update",
            data=location_data,
        ))

    @pytest.mark.asyncio
    async def test_broadcast_without_channel_layer(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should handle missing channel layer gracefully."""
        location_data = {"id": 123}

        with patch("my_tracks.mqtt.plugin.get_channel_layer_lazy", return_value=None):
            # Should not raise
            await plugin._broadcast_location(location_data)

    @pytest.mark.asyncio
    async def test_broadcast_handles_exception(
        self,
        plugin: OwnTracksPlugin,
    ) -> None:
        """Should handle broadcast exceptions gracefully."""
        mock_layer = AsyncMock()
        mock_layer.group_send = AsyncMock(side_effect=Exception("Test error"))

        location_data = {"id": 123}

        with patch("my_tracks.mqtt.plugin.get_channel_layer_lazy", return_value=mock_layer):
            # Should not raise
            await plugin._broadcast_location(location_data)
