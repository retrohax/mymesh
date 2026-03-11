# mymesh

Python utilities for interacting with a [Meshtastic](https://meshtastic.org/) LoRa mesh radio network via serial.

## Requirements

- Python 3.8+
- A Meshtastic-compatible device connected via USB
- [meshtastic](https://pypi.org/project/meshtastic/) Python library

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install meshtastic pypubsub
```

## Scripts

### `show_nodes.py`

Connects to the device and prints a table of all nodes currently known to the mesh.

```bash
python show_nodes.py
```

Output columns: Node ID, Long Name, Short Name, SNR, Last Heard, Battery.

---

### `listener.py`

Listens in real time and prints any public (broadcast) text messages received over the mesh.

```bash
python listener.py
```

Press `Ctrl+C` to stop.

## Device

Both scripts default to `/dev/ttyUSB1`. Change the `devPath` argument in either script if your device is on a different port (e.g. `/dev/ttyUSB0` or `/dev/ttyACM0`).
