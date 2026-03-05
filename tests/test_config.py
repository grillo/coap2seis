"""Tests for configuration loading and validation."""

import os
import tempfile

import pytest

from coap2seis.config import Config


class TestFromYaml:
    def test_valid_config(self):
        content = """
output: pyew
coap:
  port: 5684
earthworm:
  ring_name: WAVE_RING
  module_id: 150
  installation_id: 141
  heartbeat_interval: 30
network: "GR"
location: "00"
buffer:
  target_samples: 250
  max_age_seconds: 1.0
logging:
  level: INFO
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            f.flush()
            cfg = Config.from_yaml(f.name)

        os.unlink(f.name)
        assert cfg.coap_port == 5684
        assert cfg.ring_name == "WAVE_RING"
        assert cfg.module_id == 150
        assert cfg.network == "GR"
        assert cfg.location == "00"
        assert cfg.output == "pyew"

    def test_minimal_config(self):
        """Only required sections, defaults for everything else."""
        content = "coap:\n  port: 9999\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            f.flush()
            cfg = Config.from_yaml(f.name)

        os.unlink(f.name)
        assert cfg.coap_port == 9999
        assert cfg.ring_name == "WAVE_RING"  # default

    def test_miniseed_output(self):
        content = """
output: miniseed
miniseed:
  output_dir: /tmp/mseed
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(content)
            f.flush()
            cfg = Config.from_yaml(f.name)

        os.unlink(f.name)
        assert cfg.output == "miniseed"
        assert cfg.mseed_dir == "/tmp/mseed"

    def test_invalid_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("just a string")
            f.flush()
        with pytest.raises(ValueError, match="Invalid config"):
            Config.from_yaml(f.name)
        os.unlink(f.name)


class TestValidation:
    def test_invalid_port(self):
        with pytest.raises(ValueError, match="port"):
            Config(coap_port=0).validate()
        with pytest.raises(ValueError, match="port"):
            Config(coap_port=70000).validate()

    def test_invalid_output_mode(self):
        with pytest.raises(ValueError, match="output mode"):
            Config(output="foobar").validate()

    def test_invalid_location_too_long(self):
        with pytest.raises(ValueError, match="Location"):
            Config(location="ABC").validate()

    def test_invalid_network_too_long(self):
        with pytest.raises(ValueError, match="Network"):
            Config(network="TOOLONGNET").validate()

    def test_invalid_target_samples(self):
        with pytest.raises(ValueError, match="target_samples"):
            Config(target_samples=0).validate()

    def test_invalid_max_age(self):
        with pytest.raises(ValueError, match="max_age"):
            Config(max_age_seconds=0).validate()

    def test_invalid_heartbeat(self):
        with pytest.raises(ValueError, match="heartbeat"):
            Config(heartbeat_interval=0).validate()

    def test_valid_defaults(self):
        """Default config should pass validation."""
        Config().validate()
