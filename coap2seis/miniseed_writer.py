"""miniSEED file output backend.

Writes waveform data as miniSEED files to a directory, organized by date.
ObsPy reads these natively. Good for archiving and research use.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class MiniSeedWriter:
    """Writes waveform data as miniSEED files.

    File structure: {output_dir}/{network}.{station}.{location}.{channel}.{date}.mseed
    New file per day per SCNL.
    """

    def __init__(self, output_dir: str):
        from obspy import Stream  # fail fast if obspy not installed

        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._alive = True
        logger.info("miniSEED output directory: %s", self._output_dir)

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
        from obspy import Trace, Stream, UTCDateTime

        tr = Trace(data=samples)
        tr.stats.network = network
        tr.stats.station = station
        tr.stats.location = location
        tr.stats.channel = channel
        tr.stats.sampling_rate = float(sample_rate)
        tr.stats.starttime = UTCDateTime(start_time)

        dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
        date_str = dt.strftime("%Y%m%d")
        filename = f"{network}.{station}.{location}.{channel}.{date_str}.mseed"
        path = self._output_dir / filename

        st = Stream([tr])
        if path.exists():
            existing = Stream()
            try:
                from obspy import read
                existing = read(str(path))
            except Exception:
                pass
            existing += st
            existing.write(str(path), format="MSEED")
        else:
            st.write(str(path), format="MSEED")

        logger.debug("Wrote %d samples to %s", len(samples), filename)

    def heartbeat(self) -> None:
        pass

    def is_alive(self) -> bool:
        return self._alive

    def shutdown(self) -> None:
        self._alive = False
        logger.info("miniSEED writer shut down")
