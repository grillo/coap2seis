"""Main orchestrator tying CoAP ingestion to output backends."""

from __future__ import annotations

import asyncio
import logging
import queue
import signal
import threading
import time
from dataclasses import dataclass

import numpy as np

from .buffer import ChannelBuffer, FlushResult
from .coap_server import create_coap_server
from .config import Config
from .payload import SensorPacket, parse_json_payload
from .writer import Writer

logger = logging.getLogger(__name__)


@dataclass
class WaveMessage:
    station: str
    channel: str
    network: str
    location: str
    samples: np.ndarray
    sample_rate: int
    start_time: float


class CoAP2EW:
    """Bridges CoAP sensor data to an output Writer backend."""

    def __init__(self, config: Config, writer: Writer):
        self._config = config
        self._writer = writer
        self._buffers: dict[tuple[str, str], ChannelBuffer] = {}
        self._device_scnl: dict[str, tuple[str, str]] = {}  # dev_id -> (station, network)
        self._queue: queue.Queue[WaveMessage | None] = queue.Queue()
        self._shutdown_event = asyncio.Event()
        self._packet_count = 0

    async def run(self):
        loop = asyncio.get_running_loop()

        # Signal handling
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown_event.set)

        # Start CoAP server
        coap_ctx = await create_coap_server(
            "0.0.0.0", self._config.coap_port, self._on_packet
        )

        # Start writer thread
        writer_thread = threading.Thread(
            target=self._writer_worker, daemon=True, name="ew-writer"
        )
        writer_thread.start()

        # Periodic flush task
        flush_task = asyncio.create_task(self._periodic_flush())

        logger.info("Bridge running. Waiting for sensor data...")

        # Wait for shutdown
        await self._shutdown_event.wait()
        logger.info("Shutting down...")

        flush_task.cancel()
        # Flush all remaining buffers
        self._flush_all()
        # Signal writer thread to stop
        self._queue.put(None)
        writer_thread.join(timeout=5.0)

        await coap_ctx.shutdown()
        logger.info("Bridge stopped. Processed %d packets.", self._packet_count)

    async def _on_packet(
        self, device_type: str | None, device_id: str | None, payload: bytes
    ):
        """Called by CoAP server for each incoming POST."""
        packet = parse_json_payload(payload, device_type)

        # Use device_id from URI if available, else from payload
        dev_id = device_id or packet.device_id

        # Apply config overrides
        network = self._config.network or packet.network
        location = self._config.location
        station = packet.station

        # Cache SCNL for periodic/shutdown flushes
        self._device_scnl[dev_id] = (station, network)

        self._packet_count += 1
        if self._packet_count == 1:
            logger.info("First packet from %s (%s.%s) sr=%d ch=%s",
                        dev_id, network, station, packet.sample_rate,
                        ",".join(packet.channels.keys()))
        if self._packet_count % 100 == 0:
            logger.info("Received %d packets from %s", self._packet_count, dev_id)

        for chan_code, samples in packet.channels.items():
            buf_key = (dev_id, chan_code)
            if buf_key not in self._buffers:
                self._buffers[buf_key] = ChannelBuffer(
                    self._config.target_samples, self._config.max_age_seconds
                )
            buf = self._buffers[buf_key]
            results = buf.append(samples, packet.timestamp_us, packet.sample_rate)
            for result in results:
                self._enqueue(station, chan_code, network, location,
                              result, packet.sample_rate)

    def _enqueue(
        self, station: str, channel: str, network: str, location: str,
        result: FlushResult, sample_rate: int,
    ):
        msg = WaveMessage(
            station=station,
            channel=channel,
            network=network,
            location=location,
            samples=result.samples,
            sample_rate=result.sample_rate,
            start_time=result.start_time,
        )
        self._queue.put(msg)

    def _make_wave_msg(self, dev_id: str, chan_code: str, result: FlushResult) -> WaveMessage:
        station, network = self._device_scnl.get(dev_id, ("", ""))
        return WaveMessage(
            station=station,
            channel=chan_code,
            network=network or self._config.network,
            location=self._config.location,
            samples=result.samples,
            sample_rate=result.sample_rate,
            start_time=result.start_time,
        )

    async def _periodic_flush(self):
        """Flush aged buffers every 250ms."""
        try:
            while True:
                await asyncio.sleep(0.25)
                for (dev_id, chan_code), buf in list(self._buffers.items()):
                    result = buf.flush_if_aged()
                    if result is not None:
                        self._queue.put(self._make_wave_msg(dev_id, chan_code, result))
        except asyncio.CancelledError:
            pass

    def _flush_all(self):
        """Flush all buffers on shutdown."""
        for (dev_id, chan_code), buf in self._buffers.items():
            result = buf.flush_if_aged()
            if result is None:
                result = buf._flush()
            if result is not None:
                self._queue.put(self._make_wave_msg(dev_id, chan_code, result))

    def _writer_worker(self):
        """Thread that drains the queue and writes to the backend."""
        hb_interval = self._config.heartbeat_interval
        last_hb = time.monotonic()

        while True:
            try:
                msg = self._queue.get(timeout=1.0)
            except queue.Empty:
                # Heartbeat check
                if time.monotonic() - last_hb >= hb_interval:
                    self._writer.heartbeat()
                    last_hb = time.monotonic()
                continue

            if msg is None:
                break

            try:
                self._writer.put_wave(
                    station=msg.station,
                    channel=msg.channel,
                    network=msg.network,
                    location=msg.location,
                    samples=msg.samples,
                    sample_rate=msg.sample_rate,
                    start_time=msg.start_time,
                )
                logger.info("Wrote %s.%s.%s.%s %d samples",
                            msg.network, msg.station, msg.location, msg.channel,
                            len(msg.samples))
            except Exception:
                logger.exception("Failed to write wave")

            if time.monotonic() - last_hb >= hb_interval:
                self._writer.heartbeat()
                last_hb = time.monotonic()

        self._writer.shutdown()
