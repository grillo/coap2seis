"""Pluggable output backend protocol.

Backends implement this interface to receive buffered waveform data.
Built-in backends: earthworm (PyEW), miniseed (file output).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Writer(Protocol):
    """Output backend for waveform data."""

    def put_wave(
        self,
        station: str,
        channel: str,
        network: str,
        location: str,
        samples: np.ndarray,
        sample_rate: int,
        start_time: float,
    ) -> None:
        """Write a waveform packet."""
        ...

    def heartbeat(self) -> None:
        """Periodic keep-alive (no-op for backends that don't need it)."""
        ...

    def is_alive(self) -> bool:
        """Return True if the backend is healthy."""
        ...

    def shutdown(self) -> None:
        """Clean up resources."""
        ...
