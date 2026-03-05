"""Per-channel sample accumulator with gap detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


@dataclass
class FlushResult:
    samples: np.ndarray  # int32
    start_time: float    # seconds since epoch
    sample_rate: int


class ChannelBuffer:
    """Accumulates samples for a single (device, channel) pair.

    Flushes when target sample count reached, max age exceeded, or gap detected.
    """

    def __init__(self, target_samples: int, max_age_seconds: float):
        self._target = target_samples
        self._max_age = max_age_seconds
        self._samples: list[int] = []
        self._start_time: float | None = None  # seconds
        self._sample_rate: int = 0
        self._expected_next_us: int | None = None  # microseconds
        self._created_at: float | None = None

    def append(self, samples: list[int], timestamp_us: int, sample_rate: int) -> list[FlushResult]:
        """Add samples to buffer. Returns list of FlushResults (0, 1, or 2 if gap detected)."""
        results: list[FlushResult] = []

        # Gap detection: if expected timestamp differs from actual by > 1.5 sample intervals
        if self._expected_next_us is not None and self._samples:
            interval_us = 1_000_000 / sample_rate
            drift = abs(timestamp_us - self._expected_next_us)
            if drift > 1.5 * interval_us:
                flushed = self._flush()
                if flushed:
                    results.append(flushed)

        # First sample in buffer sets the start time
        if not self._samples:
            self._start_time = timestamp_us / 1_000_000.0
            self._sample_rate = sample_rate
            self._created_at = time.monotonic()

        self._samples.extend(samples)
        self._expected_next_us = timestamp_us + int(len(samples) * 1_000_000 / sample_rate)

        # Flush if target reached
        if len(self._samples) >= self._target:
            flushed = self._flush()
            if flushed:
                results.append(flushed)

        return results

    def flush_if_aged(self) -> FlushResult | None:
        """Flush buffer if it has exceeded max age. Called periodically."""
        if not self._samples or self._created_at is None:
            return None
        if time.monotonic() - self._created_at >= self._max_age:
            return self._flush()
        return None

    def _flush(self) -> FlushResult | None:
        if not self._samples:
            return None
        result = FlushResult(
            samples=np.array(self._samples, dtype=np.int32),
            start_time=self._start_time,
            sample_rate=self._sample_rate,
        )
        self._samples = []
        self._start_time = None
        self._sample_rate = 0
        self._created_at = None
        # Keep _expected_next_us so next append can detect gaps
        return result
