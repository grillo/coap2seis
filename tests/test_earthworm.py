"""Tests for EarthwormWriter with mocked PyEW."""

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def mock_pyew():
    """Mock the PyEW module since it requires Earthworm to be installed."""
    mock_module = MagicMock()
    mock_module.add_ring.return_value = 0
    mock_module.mod_sta.return_value = 0

    mock_pyew = MagicMock()
    mock_pyew.EWModule.return_value = mock_module

    with patch.dict(sys.modules, {"PyEW": mock_pyew}):
        yield mock_pyew, mock_module


class TestEarthwormWriter:
    def test_init(self, mock_pyew):
        mock_pkg, mock_mod = mock_pyew
        from coap2seis.earthworm import EarthwormWriter

        writer = EarthwormWriter("WAVE_RING", module_id=150, installation_id=141)
        mock_pkg.EWModule.assert_called_once_with(150, 141, 0, False)
        mock_mod.add_ring.assert_called_once_with("WAVE_RING")

    def test_put_wave(self, mock_pyew):
        mock_pkg, mock_mod = mock_pyew
        from coap2seis.earthworm import EarthwormWriter

        writer = EarthwormWriter("WAVE_RING", module_id=150, installation_id=141)
        samples = np.array([1, 2, 3, 4, 5], dtype=np.int32)

        writer.put_wave(
            station="GRL01",
            channel="HNZ",
            network="GR",
            location="00",
            samples=samples,
            sample_rate=125,
            start_time=1700000000.0,
        )

        mock_mod.put_wave.assert_called_once()
        call_args = mock_mod.put_wave.call_args
        ring_idx, wave = call_args[0]
        assert ring_idx == 0
        assert wave["station"] == "GRL01"
        assert wave["channel"] == "HNZ"
        assert wave["network"] == "GR"
        assert wave["location"] == "00"
        assert wave["nsamp"] == 5
        assert wave["samprate"] == 125.0
        assert wave["startt"] == 1700000000.0
        assert wave["endt"] == pytest.approx(1700000000.0 + 4 / 125)
        assert wave["datatype"] == "i4"
        np.testing.assert_array_equal(wave["data"], samples)

    def test_heartbeat(self, mock_pyew):
        _, mock_mod = mock_pyew
        from coap2seis.earthworm import EarthwormWriter

        writer = EarthwormWriter("WAVE_RING", module_id=150, installation_id=141)
        writer.heartbeat()
        assert mock_mod.mod_sta.call_count >= 1

    def test_is_alive(self, mock_pyew):
        _, mock_mod = mock_pyew
        from coap2seis.earthworm import EarthwormWriter

        writer = EarthwormWriter("WAVE_RING", module_id=150, installation_id=141)
        mock_mod.mod_sta.return_value = 0
        assert writer.is_alive() is True
        mock_mod.mod_sta.return_value = 1
        assert writer.is_alive() is False

    def test_shutdown(self, mock_pyew):
        _, mock_mod = mock_pyew
        from coap2seis.earthworm import EarthwormWriter

        writer = EarthwormWriter("WAVE_RING", module_id=150, installation_id=141)
        writer.shutdown()
        mock_mod.goodbye.assert_called_once()
