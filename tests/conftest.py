"""Shared fixtures for coap2seis tests."""

import pytest


@pytest.fixture
def valid_json_payload():
    """A valid 3-channel JSON payload as bytes."""
    import json
    return json.dumps({
        "d": "AABBCCDDEEFF",
        "t": 1700000000000000,
        "n": "GR",
        "st": "GRL01",
        "sr": 125,
        "HNE": list(range(50)),
        "HNN": list(range(50)),
        "HNZ": list(range(50)),
    }).encode()


@pytest.fixture
def valid_pulse_payload():
    """A valid 4-channel (pulse) JSON payload as bytes."""
    import json
    return json.dumps({
        "d": "112233445566",
        "t": 1700000000000000,
        "n": "GR",
        "st": "PLS01",
        "sr": 100,
        "HNE": list(range(25)),
        "HNN": list(range(25)),
        "HNZ": list(range(25)),
        "EHZ": list(range(25)),
    }).encode()
