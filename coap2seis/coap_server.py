"""aiocoap server with PathCapable resource for sensor data ingestion."""

from __future__ import annotations

import logging
import re
from typing import Awaitable, Callable

import aiocoap
import aiocoap.resource

logger = logging.getLogger(__name__)

DEVICE_ID_RE = re.compile(r"^[0-9A-Fa-f]{12}$")
VALID_DEVICE_TYPES = ("one", "pulse")

# Callback signature: async def(device_type, device_id, payload_bytes)
PacketCallback = Callable[[str | None, str, bytes], Awaitable[None]]


class SensorDataResource(aiocoap.resource.Resource, aiocoap.resource.PathCapable):
    """Handles POST requests at /data/{device_type}/{device_id}/json.

    Also supports legacy paths:
      /data/{device_id}/json
      /data  (device_id extracted from payload)
    """

    def __init__(self, callback: PacketCallback):
        super().__init__()
        self._callback = callback

    async def render_post(self, request: aiocoap.Message) -> aiocoap.Message:
        path = request.opt.uri_path  # tuple of path segments after the resource root
        # The resource is mounted at ("data",), so path contains segments after "data"

        device_type: str | None = None
        device_id: str | None = None

        if len(path) == 3:
            # /data/{device_type}/{device_id}/{format}
            device_type, device_id, fmt = path
            if device_type not in VALID_DEVICE_TYPES:
                return aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                       payload=b"Invalid device type")
            if fmt != "json":
                return aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                       payload=b"Only JSON format supported")
        elif len(path) == 2:
            # /data/{device_id}/{format}  (legacy)
            device_id, fmt = path
            if fmt != "json":
                return aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                       payload=b"Only JSON format supported")
        elif len(path) == 0:
            # /data  (device_id from payload)
            pass
        else:
            return aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                   payload=b"Invalid path")

        if device_id is not None and not DEVICE_ID_RE.match(device_id):
            return aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                   payload=b"Invalid device ID")

        if not request.payload:
            return aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                   payload=b"Empty payload")

        try:
            await self._callback(device_type, device_id, request.payload)
        except ValueError as e:
            logger.warning("Bad payload from %s: %s", device_id or "unknown", e)
            return aiocoap.Message(code=aiocoap.BAD_REQUEST,
                                   payload=str(e).encode())
        except Exception:
            logger.exception("Error processing packet from %s", device_id or "unknown")
            return aiocoap.Message(code=aiocoap.INTERNAL_SERVER_ERROR)

        return aiocoap.Message(code=aiocoap.CHANGED)


async def create_coap_server(
    bind: str, port: int, callback: PacketCallback
) -> aiocoap.Context:
    root = aiocoap.resource.Site()
    root.add_resource(("data",), SensorDataResource(callback))

    context = await aiocoap.Context.create_server_context(
        root, bind=(bind, port)
    )
    logger.info("CoAP server listening on %s:%d", bind, port)
    return context
