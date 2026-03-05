"""Entry point: python -m coap2seis [--config config.yaml] [--output pyew|miniseed]"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .config import Config, OUTPUT_MODES


def create_writer(config: Config):
    """Create the appropriate writer backend based on config."""
    if config.output == "pyew":
        from .earthworm import EarthwormWriter
        return EarthwormWriter(
            ring_name=config.ring_name,
            module_id=config.module_id,
            installation_id=config.installation_id,
        )
    elif config.output == "miniseed":
        from .miniseed_writer import MiniSeedWriter
        return MiniSeedWriter(output_dir=config.mseed_dir)
    else:
        raise ValueError(f"Unknown output mode: {config.output}")


def main():
    parser = argparse.ArgumentParser(
        prog="coap2seis",
        description="Grillo CoAP seismic data bridge",
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to YAML config file. If omitted, prompts interactively.",
    )
    parser.add_argument(
        "-o", "--output",
        choices=OUTPUT_MODES,
        default="pyew",
        help="Output backend (default: pyew)",
    )
    args = parser.parse_args()

    if args.config:
        config = Config.from_yaml(args.config)
        # CLI --output overrides config file
        if args.output:
            config.output = args.output
            config.validate()
    else:
        config = Config.from_interactive(output=args.output)

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        writer = create_writer(config)
    except ImportError as e:
        if "PyEW" in str(e):
            print("Error: PyEW not installed. Install Earthworm + PyEW, or use --output miniseed.", file=sys.stderr)
        elif "obspy" in str(e):
            print("Error: ObsPy not installed. pip install obspy, or use --output pyew.", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    from .bridge import CoAP2EW
    bridge = CoAP2EW(config, writer)
    asyncio.run(bridge.run())


if __name__ == "__main__":
    main()
