"""
MQTT Plugin for processing OwnTracks messages.

This plugin intercepts MQTT messages published to the broker and processes
OwnTracks location messages, saving them to the database and broadcasting
to WebSocket clients.
"""

import logging
from typing import TYPE_CHECKING, Any

from amqtt.broker import BrokerContext
from amqtt.plugins.base import BasePlugin
from amqtt.session import ApplicationMessage
from asgiref.sync import sync_to_async

from my_tracks.mqtt.handlers import OwnTracksMessageHandler

if TYPE_CHECKING:
    from channels.layers import BaseChannelLayer

logger = logging.getLogger(__name__)


def get_channel_layer_lazy() -> "BaseChannelLayer | None":
    """Get channel layer with lazy import to avoid Django setup issues."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


def save_location_to_db(location_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Save location data to the database.

    This function creates a Location model instance from the parsed
    OwnTracks message data.

    Args:
        location_data: Parsed location data from OwnTracksMessageHandler

    Returns:
        Serialized location data for WebSocket broadcast, or None on failure
    """
    # Lazy import to avoid Django setup issues during module load
    from my_tracks.models import Device, Location
    from my_tracks.serializers import LocationSerializer

    try:
        # Get or create the device
        device_id = location_data["device"]
        device, _created = Device.objects.get_or_create(
            device_id=device_id,
            defaults={"name": f"Device {device_id}"},
        )

        # Create location from parsed data
        location = Location.objects.create(
            device=device,
            latitude=location_data["latitude"],
            longitude=location_data["longitude"],
            timestamp=location_data["timestamp"],
            tracker_id=location_data.get("tracker_id", ""),
            accuracy=location_data.get("accuracy"),
            altitude=location_data.get("altitude"),
            velocity=location_data.get("velocity"),
            battery_level=location_data.get("battery"),
        )

        # Serialize for WebSocket broadcast
        serializer = LocationSerializer(location)
        # Cast to dict - serializer.data is ReturnDict which is dict-like
        return dict(serializer.data)

    except Exception:
        logger.exception("Failed to save location from MQTT message")
        return None


class OwnTracksPlugin(BasePlugin[BrokerContext]):
    """
    MQTT Plugin that processes OwnTracks messages.

    This plugin hooks into the broker's message_received event and processes
    OwnTracks-formatted MQTT messages, saving locations to the database
    and broadcasting updates to WebSocket clients.
    """

    def __init__(self, context: BrokerContext) -> None:
        """Initialize the OwnTracks plugin."""
        super().__init__(context)
        self._handler = OwnTracksMessageHandler()
        self._setup_callbacks()
        logger.info("OwnTracksPlugin initialized")

    def _setup_callbacks(self) -> None:
        """Register callbacks for different message types."""
        self._handler.on_location(self._handle_location)
        self._handler.on_lwt(self._handle_lwt)
        self._handler.on_transition(self._handle_transition)

    async def _handle_location(self, location_data: dict[str, Any]) -> None:
        """
        Handle a parsed location message.

        Saves to database and broadcasts via WebSocket.
        """
        logger.debug(
            "Processing MQTT location: device=%s, lat=%s, lon=%s",
            location_data.get("device"),
            location_data.get("latitude"),
            location_data.get("longitude"),
        )

        # Save to database (sync operation wrapped for async)
        serialized = await sync_to_async(save_location_to_db)(location_data)
        if serialized is None:
            return

        logger.info(
            "MQTT location saved: id=%s, device=%s",
            serialized.get("id"),
            serialized.get("device_id_display"),
        )

        # Broadcast via WebSocket
        await self._broadcast_location(serialized)

    async def _handle_lwt(self, lwt_data: dict[str, Any]) -> None:
        """
        Handle a parsed LWT (Last Will and Testament) message.

        LWT messages indicate a device has gone offline.
        """
        logger.info(
            "Device offline via MQTT LWT: device=%s",
            lwt_data.get("device"),
        )
        # TODO: Update device status in database when device model supports it

    async def _handle_transition(self, transition_data: dict[str, Any]) -> None:
        """
        Handle a parsed transition message.

        Transition messages indicate region enter/exit events.
        """
        logger.info(
            "MQTT transition: device=%s, event=%s, region=%s",
            transition_data.get("device"),
            transition_data.get("event"),
            transition_data.get("description"),
        )
        # TODO: Store transition events when model supports it

    async def _broadcast_location(self, location_data: dict[str, Any]) -> None:
        """
        Broadcast a location update to WebSocket clients.

        Args:
            location_data: Serialized location data to broadcast
        """
        channel_layer = get_channel_layer_lazy()
        if channel_layer is None:
            logger.warning("WebSocket broadcast skipped: no channel layer configured")
            return

        try:
            await channel_layer.group_send(
                "locations",
                {
                    "type": "location_update",
                    "data": location_data,
                },
            )
            logger.debug(
                "WebSocket broadcast sent for MQTT location id=%s",
                location_data.get("id"),
            )
        except Exception:
            logger.exception("WebSocket broadcast failed for MQTT location")

    async def on_broker_message_received(
        self,
        *,
        client_id: str,
        message: ApplicationMessage,
    ) -> None:
        """
        Process a message received by the broker.

        This is the main hook that amqtt calls for each published message.

        Args:
            client_id: The client ID that published the message
            message: The application message containing topic and payload
        """
        topic = message.topic

        # Quick filter: only process owntracks topics
        if not topic.startswith("owntracks/"):
            return

        logger.debug(
            "MQTT message received: client=%s, topic=%s, size=%d",
            client_id,
            topic,
            len(message.data) if message.data else 0,
        )

        # Process through OwnTracks handler
        # Convert bytearray to bytes if needed
        payload = bytes(message.data) if isinstance(message.data, bytearray) else message.data
        await self._handler.handle_message(topic, payload)
