"""PyEW wrapper: put_wave, heartbeat, shutdown."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class EarthwormWriter:
    """Wraps PyEW.EWModule for writing TRACEBUF2 messages to a ring."""

    def __init__(self, ring_name: str, module_id: int, installation_id: int):
        import PyEW

        self._module = PyEW.EWModule(module_id, installation_id, 0, False)
        self._ring_idx = self._module.add_ring(ring_name)
        self._ring_name = ring_name
        logger.info("Connected to Earthworm ring %r (module=%d, inst=%d)",
                     ring_name, module_id, installation_id)

    def put_wave(
        self,
        station: str,
        channel: str,
        network: str,
        location: str,
        samples: np.ndarray,
        sample_rate: int,
        start_time: float,
    ):
        """Write a TRACEBUF2 message to the ring."""
        nsamp = len(samples)
        wave = {
            "station": station,
            "channel": channel,
            "network": network,
            "location": location,
            "nsamp": nsamp,
            "samprate": float(sample_rate),
            "startt": start_time,
            "endt": start_time + (nsamp - 1) / sample_rate,
            "datatype": "i4",
            "data": samples,
        }
        self._module.put_wave(self._ring_idx, wave)

    def heartbeat(self):
        self._module.mod_sta()

    def is_alive(self) -> bool:
        return self._module.mod_sta() == 0

    def shutdown(self):
        logger.info("Sending goodbye to Earthworm")
        self._module.goodbye()
