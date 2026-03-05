"""Configuration loading: interactive prompts, CLI args, or YAML file."""

from __future__ import annotations

import sys
from dataclasses import dataclass

import yaml

OUTPUT_MODES = ("pyew", "miniseed")


@dataclass
class Config:
    # Output
    output: str = "pyew"       # pyew, miniseed

    # CoAP
    coap_port: int = 5684

    # Earthworm (only used when output=pyew)
    ring_name: str = "WAVE_RING"
    module_id: int = 150
    installation_id: int = 141
    heartbeat_interval: int = 30

    # miniSEED (only used when output=miniseed)
    mseed_dir: str = "./mseed_out"

    # SCNL overrides
    network: str = ""      # empty = use sensor value
    location: str = "00"

    # Buffer
    target_samples: int = 250
    max_age_seconds: float = 1.0

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: str) -> Config:
        with open(path) as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid config file: {path}")

        c = cls()
        c.output = str(raw.get("output", c.output))

        coap = raw.get("coap", {})
        c.coap_port = int(coap.get("port", c.coap_port))

        ew = raw.get("earthworm", {})
        c.ring_name = str(ew.get("ring_name", c.ring_name))
        c.module_id = int(ew.get("module_id", c.module_id))
        c.installation_id = int(ew.get("installation_id", c.installation_id))
        c.heartbeat_interval = int(ew.get("heartbeat_interval", c.heartbeat_interval))

        ms = raw.get("miniseed", {})
        c.mseed_dir = str(ms.get("output_dir", c.mseed_dir))

        c.network = str(raw.get("network", c.network))
        c.location = str(raw.get("location", c.location))

        buf = raw.get("buffer", {})
        c.target_samples = int(buf.get("target_samples", c.target_samples))
        c.max_age_seconds = float(buf.get("max_age_seconds", c.max_age_seconds))

        log = raw.get("logging", {})
        c.log_level = str(log.get("level", c.log_level))

        c.validate()
        return c

    @classmethod
    def from_interactive(cls, output: str = "pyew") -> Config:
        """Prompt user for settings with defaults. Enter through for defaults."""
        c = cls(output=output)

        def ask(prompt: str, default):
            display = default if default != "" else "<sensor>"
            val = input(f"{prompt} [{display}]: ").strip()
            return val if val else default

        try:
            c.coap_port = int(ask("CoAP port", c.coap_port))

            if output == "pyew":
                c.ring_name = str(ask("Earthworm ring", c.ring_name))
                c.module_id = int(ask("Module ID", c.module_id))
                c.installation_id = int(ask("Installation ID", c.installation_id))
                c.heartbeat_interval = int(ask("Heartbeat interval", c.heartbeat_interval))
            elif output == "miniseed":
                c.mseed_dir = str(ask("miniSEED output dir", c.mseed_dir))

            c.network = str(ask("Network", c.network))
            c.location = str(ask("Location code", c.location))
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        c.validate()
        return c

    def validate(self):
        if self.output not in OUTPUT_MODES:
            raise ValueError(f"Invalid output mode: {self.output!r}, must be one of {OUTPUT_MODES}")
        if not 1 <= self.coap_port <= 65535:
            raise ValueError(f"Invalid CoAP port: {self.coap_port}")
        if self.output == "pyew":
            if self.module_id < 0:
                raise ValueError(f"Invalid module_id: {self.module_id}")
            if self.installation_id < 0:
                raise ValueError(f"Invalid installation_id: {self.installation_id}")
            if self.heartbeat_interval < 1:
                raise ValueError(f"Invalid heartbeat_interval: {self.heartbeat_interval}")
        if self.target_samples < 1:
            raise ValueError(f"Invalid target_samples: {self.target_samples}")
        if self.max_age_seconds <= 0:
            raise ValueError(f"Invalid max_age_seconds: {self.max_age_seconds}")
        if len(self.location) > 2:
            raise ValueError(f"Location code must be <= 2 chars: {self.location!r}")
        if len(self.network) > 8:
            raise ValueError(f"Network code must be <= 8 chars: {self.network!r}")
