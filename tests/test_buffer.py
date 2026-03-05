"""Tests for per-channel buffer accumulation and flushing."""

import time
from unittest.mock import patch

import numpy as np
import pytest

from coap2seis.buffer import ChannelBuffer


class TestAccumulation:
    def test_no_flush_below_target(self):
        buf = ChannelBuffer(target_samples=100, max_age_seconds=10.0)
        results = buf.append([1, 2, 3], timestamp_us=1000000, sample_rate=125)
        assert results == []

    def test_flush_at_target(self):
        buf = ChannelBuffer(target_samples=10, max_age_seconds=10.0)
        results = buf.append(list(range(10)), timestamp_us=1000000, sample_rate=125)
        assert len(results) == 1
        assert len(results[0].samples) == 10
        np.testing.assert_array_equal(results[0].samples, np.arange(10, dtype=np.int32))

    def test_flush_over_target(self):
        """Samples exceeding target still get flushed together."""
        buf = ChannelBuffer(target_samples=5, max_age_seconds=10.0)
        results = buf.append(list(range(8)), timestamp_us=1000000, sample_rate=125)
        assert len(results) == 1
        assert len(results[0].samples) == 8

    def test_accumulate_multiple_appends(self):
        buf = ChannelBuffer(target_samples=10, max_age_seconds=10.0)
        buf.append([1, 2, 3], timestamp_us=1000000, sample_rate=125)
        buf.append([4, 5, 6], timestamp_us=1024000, sample_rate=125)
        results = buf.append([7, 8, 9, 10], timestamp_us=1048000, sample_rate=125)
        assert len(results) == 1
        assert len(results[0].samples) == 10


class TestStartTime:
    def test_start_time_from_first_sample(self):
        buf = ChannelBuffer(target_samples=5, max_age_seconds=10.0)
        results = buf.append([1, 2, 3, 4, 5], timestamp_us=2000000000, sample_rate=125)
        assert results[0].start_time == pytest.approx(2000.0)

    def test_start_time_resets_after_flush(self):
        buf = ChannelBuffer(target_samples=3, max_age_seconds=10.0)
        r1 = buf.append([1, 2, 3], timestamp_us=1000000, sample_rate=125)
        r2 = buf.append([4, 5, 6], timestamp_us=1024000, sample_rate=125)
        assert r1[0].start_time == pytest.approx(1.0)
        assert r2[0].start_time == pytest.approx(1.024)


class TestGapDetection:
    def test_gap_triggers_flush(self):
        buf = ChannelBuffer(target_samples=100, max_age_seconds=10.0)
        buf.append([1, 2, 3], timestamp_us=1000000, sample_rate=125)
        # Gap: jump 1 second forward (125 samples at 125Hz = 1s)
        results = buf.append([4, 5, 6], timestamp_us=2000000, sample_rate=125)
        # Should get a flush of the first batch due to gap
        assert len(results) == 1
        np.testing.assert_array_equal(results[0].samples, [1, 2, 3])

    def test_no_gap_within_tolerance(self):
        buf = ChannelBuffer(target_samples=100, max_age_seconds=10.0)
        buf.append([1, 2, 3], timestamp_us=1000000, sample_rate=125)
        # Next packet at expected time (3 samples at 125Hz = 24000us later)
        results = buf.append([4, 5, 6], timestamp_us=1024000, sample_rate=125)
        assert results == []


class TestAgeFlush:
    def test_flush_if_aged(self):
        buf = ChannelBuffer(target_samples=100, max_age_seconds=0.01)
        buf.append([1, 2, 3], timestamp_us=1000000, sample_rate=125)
        time.sleep(0.02)
        result = buf.flush_if_aged()
        assert result is not None
        assert len(result.samples) == 3

    def test_no_flush_if_not_aged(self):
        buf = ChannelBuffer(target_samples=100, max_age_seconds=10.0)
        buf.append([1, 2, 3], timestamp_us=1000000, sample_rate=125)
        result = buf.flush_if_aged()
        assert result is None

    def test_flush_if_aged_empty_buffer(self):
        buf = ChannelBuffer(target_samples=100, max_age_seconds=0.01)
        result = buf.flush_if_aged()
        assert result is None
