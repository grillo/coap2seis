"""JSON payload parser — ported from json_payload.go."""

from __future__ import annotations

import json
from dataclasses import dataclass

MAX_SAMPLES_PER_CHANNEL = 100


@dataclass
class SensorPacket:
    device_id: str
    timestamp_us: int
    network: str
    station: str
    sample_rate: int
    channels: dict[str, list[int]]  # e.g. {"HNE": [...], "HNN": [...], "HNZ": [...]}


def parse_json_payload(data: bytes, device_type: str | None = None) -> SensorPacket:
    """Parse a JSON sensor payload.

    Args:
        data: Raw JSON bytes from CoAP packet.
        device_type: "one", "pulse", or None (auto-detect from payload).

    Returns:
        SensorPacket with parsed data.

    Raises:
        ValueError: If payload is invalid or missing required fields.
    """
    try:
        obj = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    if not isinstance(obj, dict):
        raise ValueError("Payload must be a JSON object")

    # Required scalar fields
    device_id = obj.get("d")
    if not device_id or not isinstance(device_id, str):
        raise ValueError("Missing or empty field 'd' (device_id)")

    timestamp_us = obj.get("t")
    if not isinstance(timestamp_us, (int, float)) or timestamp_us == 0:
        raise ValueError("Missing or zero field 't' (timestamp)")
    timestamp_us = int(timestamp_us)

    # Network is optional — config override used when empty
    network = obj.get("n", "")
    if not isinstance(network, str):
        network = ""

    station = obj.get("st")
    if not station or not isinstance(station, str):
        raise ValueError("Missing or empty field 'st' (station)")

    sample_rate = obj.get("sr")
    if not isinstance(sample_rate, (int, float)) or sample_rate <= 0:
        raise ValueError("Missing or invalid field 'sr' (sample_rate), must be > 0")
    sample_rate = int(sample_rate)

    # Channel data
    channels: dict[str, list[int]] = {}
    for code in ("HNE", "HNN", "HNZ"):
        samples = obj.get(code)
        if not isinstance(samples, list) or len(samples) == 0:
            raise ValueError(f"Missing or empty channel '{code}'")
        if len(samples) > MAX_SAMPLES_PER_CHANNEL:
            raise ValueError(
                f"Channel '{code}' has {len(samples)} samples, max {MAX_SAMPLES_PER_CHANNEL}"
            )
        channels[code] = samples

    # EHZ: required for pulse, optional otherwise
    ehz = obj.get("EHZ")
    if device_type == "pulse":
        if not isinstance(ehz, list) or len(ehz) == 0:
            raise ValueError("Missing or empty channel 'EHZ' (required for pulse)")
        if len(ehz) > MAX_SAMPLES_PER_CHANNEL:
            raise ValueError(
                f"Channel 'EHZ' has {len(ehz)} samples, max {MAX_SAMPLES_PER_CHANNEL}"
            )
        channels["EHZ"] = ehz
    elif isinstance(ehz, list) and len(ehz) > 0:
        if len(ehz) > MAX_SAMPLES_PER_CHANNEL:
            raise ValueError(
                f"Channel 'EHZ' has {len(ehz)} samples, max {MAX_SAMPLES_PER_CHANNEL}"
            )
        channels["EHZ"] = ehz

    return SensorPacket(
        device_id=device_id,
        timestamp_us=timestamp_us,
        network=network,
        station=station,
        sample_rate=sample_rate,
        channels=channels,
    )
