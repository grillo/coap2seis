"""Tests for JSON payload parsing."""

import json

import pytest

from coap2seis.payload import MAX_SAMPLES_PER_CHANNEL, parse_json_payload


class TestParseValidPayload:
    def test_three_channel(self, valid_json_payload):
        pkt = parse_json_payload(valid_json_payload, device_type="one")
        assert pkt.device_id == "AABBCCDDEEFF"
        assert pkt.timestamp_us == 1700000000000000
        assert pkt.network == "GR"
        assert pkt.station == "GRL01"
        assert pkt.sample_rate == 125
        assert set(pkt.channels.keys()) == {"HNE", "HNN", "HNZ"}
        assert len(pkt.channels["HNE"]) == 50

    def test_four_channel_pulse(self, valid_pulse_payload):
        pkt = parse_json_payload(valid_pulse_payload, device_type="pulse")
        assert set(pkt.channels.keys()) == {"HNE", "HNN", "HNZ", "EHZ"}
        assert len(pkt.channels["EHZ"]) == 25

    def test_ehz_included_without_device_type(self):
        """EHZ included when present even without explicit device_type."""
        data = json.dumps({
            "d": "AABBCCDDEEFF", "t": 1, "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3], "EHZ": [4],
        }).encode()
        pkt = parse_json_payload(data)
        assert "EHZ" in pkt.channels

    def test_no_device_type_no_ehz(self):
        """Without device_type and no EHZ field, only 3 channels."""
        data = json.dumps({
            "d": "AABBCCDDEEFF", "t": 1, "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        pkt = parse_json_payload(data)
        assert set(pkt.channels.keys()) == {"HNE", "HNN", "HNZ"}


class TestParseInvalidPayload:
    def test_not_json(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_payload(b"not json")

    def test_not_object(self):
        with pytest.raises(ValueError, match="must be a JSON object"):
            parse_json_payload(b"[1,2,3]")

    def test_missing_device_id(self):
        data = json.dumps({
            "t": 1, "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        with pytest.raises(ValueError, match="'d'"):
            parse_json_payload(data)

    def test_missing_timestamp(self):
        data = json.dumps({
            "d": "AABB", "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        with pytest.raises(ValueError, match="'t'"):
            parse_json_payload(data)

    def test_zero_timestamp(self):
        data = json.dumps({
            "d": "AABB", "t": 0, "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        with pytest.raises(ValueError, match="'t'"):
            parse_json_payload(data)

    def test_missing_network_defaults_empty(self):
        data = json.dumps({
            "d": "AABB", "t": 1, "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        pkt = parse_json_payload(data)
        assert pkt.network == ""

    def test_missing_station(self):
        data = json.dumps({
            "d": "AABB", "t": 1, "n": "X", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        with pytest.raises(ValueError, match="'st'"):
            parse_json_payload(data)

    def test_zero_sample_rate(self):
        data = json.dumps({
            "d": "AABB", "t": 1, "n": "X", "st": "S", "sr": 0,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        with pytest.raises(ValueError, match="'sr'"):
            parse_json_payload(data)

    def test_missing_channel(self):
        data = json.dumps({
            "d": "AABB", "t": 1, "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2],
        }).encode()
        with pytest.raises(ValueError, match="'HNZ'"):
            parse_json_payload(data)

    def test_empty_channel(self):
        data = json.dumps({
            "d": "AABB", "t": 1, "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [],
        }).encode()
        with pytest.raises(ValueError, match="'HNZ'"):
            parse_json_payload(data)

    def test_too_many_samples(self):
        data = json.dumps({
            "d": "AABB", "t": 1, "n": "X", "st": "S", "sr": 100,
            "HNE": list(range(101)), "HNN": [1], "HNZ": [1],
        }).encode()
        with pytest.raises(ValueError, match="101 samples"):
            parse_json_payload(data)

    def test_pulse_missing_ehz(self):
        data = json.dumps({
            "d": "AABB", "t": 1, "n": "X", "st": "S", "sr": 100,
            "HNE": [1], "HNN": [2], "HNZ": [3],
        }).encode()
        with pytest.raises(ValueError, match="EHZ"):
            parse_json_payload(data, device_type="pulse")
