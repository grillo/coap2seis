# coap2seis

Bridge between Grillo seismic sensors (CoAP/UDP) and Earthworm shared memory rings. Also supports miniSEED file output for ObsPy workflows.

```
Grillo Sensor --CoAP/UDP--> aiocoap server --> parse JSON --> buffer --> queue --> Writer backend
                                                                                   ├── PyEW → Earthworm Ring
                                                                                   └── miniSEED → files
```

## Install

```bash
pip install -e .

# For miniSEED output, also install ObsPy:
pip install obspy

# Note: ObsPy requires setuptools < 82 (pkg_resources was removed in 82)
pip install "setuptools<82"
```

PyEW must be installed separately alongside a working Earthworm installation.

## Usage

### Interactive (default)

```bash
python -m coap2seis
```

Prompts for settings with sensible defaults — just hit Enter to accept:

```
Output backend (pyew, miniseed) [miniseed]:
CoAP port [5684]:
miniSEED output dir [./mseed_out]:
Network [<sensor>]:
Location code [00]:
```

Choosing `pyew` instead prompts for Earthworm-specific settings (ring name, module ID, installation ID).

### Skip prompts with CLI flags

```bash
python -m coap2seis --output miniseed     # miniSEED files (requires obspy)
python -m coap2seis --output pyew          # Earthworm ring (requires PyEW)
python -m coap2seis -c config/coap2seis.yaml.example  # from config file
```

miniSEED writes `{net}.{sta}.{loc}.{cha}.{date}.mseed` files to a directory. ObsPy reads these natively.

## SCNL codes

The bridge uses FDSN codes directly from the sensor payload:

| Field | Source |
|-------|--------|
| **Station** | Sensor (`st` field) |
| **Channel** | Sensor (HNE, HNN, HNZ, EHZ) |
| **Network** | Sensor (`n` field), or `--network` override |
| **Location** | Config (default `00`) |

Set a network override to apply a consistent network code across all sensors:

```bash
python -m coap2seis  # then enter "GR" at the Network prompt
```

## CoAP endpoint

The server accepts POST requests at:

```
/data/{device_type}/{device_id}/json    # e.g. /data/one/AABBCCDDEEFF/json
/data/{device_id}/json                  # legacy format
/data                                   # device ID from payload
```

JSON payload fields: `d` (device ID), `t` (timestamp μs), `n` (network), `st` (station), `sr` (sample rate), `HNE`, `HNN`, `HNZ`, optional `EHZ`.

## Buffering

Samples accumulate per channel and flush when:

- **Target count reached** — 250 samples by default (~2s at 125 Hz)
- **Max age exceeded** — 1s by default
- **Gap detected** — timestamp discontinuity > 1.5× sample interval

TRACEBUF2 messages stay well under the 4096-byte limit (250 × 4 bytes = 1000 bytes).

## Output backends

The `Writer` protocol in `writer.py` defines the backend interface. Current backends:

| Backend | Flag | Dependency | Use case |
|---------|------|------------|----------|
| `pyew` | `--output pyew` | PyEW + Earthworm | Production EEW pipelines |
| `miniseed` | `--output miniseed` | ObsPy | Archiving, research, post-processing |

Adding a new backend (e.g. SeedLink) means implementing `put_wave()`, `heartbeat()`, `is_alive()`, and `shutdown()`.

## systemd

```bash
sudo cp config/coap2seis.yaml.example /etc/coap2seis/coap2seis.yaml
sudo cp systemd/coap2seis.service /etc/systemd/system/
sudo systemctl enable --now coap2seis
```

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
