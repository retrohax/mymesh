import meshtastic
import meshtastic.serial_interface
from meshtastic import mesh_pb2
import json
import os
import time
from datetime import datetime

def load_config():
    import sys
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(config_path):
        print(f"Error: config.json not found at {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)

def display_nodes(interface):
    nodes = interface.nodes
    if not nodes:
        print("No nodes found in the mesh.")
        return

    print(f"{'Node ID':<12} {'Long Name':<25} {'Short Name':<12} {'SNR':<8} {'Last Heard':<20} {'Battery':<10}")
    print("-" * 90)

    for node_id, node in nodes.items():
        user = node.get("user", {})
        metrics = node.get("deviceMetrics", {})
        position = node.get("position", {})

        long_name  = user.get("longName", "Unknown")
        short_name = user.get("shortName", "???")
        snr        = node.get("snr", "N/A")
        last_heard = node.get("lastHeard", None)
        if isinstance(last_heard, int) and last_heard > 0:
            age = int(time.time()) - last_heard
            if age < 60:
                last_heard_str = f"{age}s ago"
            elif age < 3600:
                last_heard_str = f"{age // 60}m ago"
            elif age < 86400:
                last_heard_str = f"{age // 3600}h {(age % 3600) // 60}m ago"
            else:
                last_heard_str = datetime.fromtimestamp(last_heard).strftime("%m/%d %H:%M")
        else:
            last_heard_str = "never"
        battery    = metrics.get("batteryLevel", "N/A")
        battery_str = f"{battery}%" if isinstance(battery, (int, float)) else str(battery)

        print(f"{node_id:<12} {long_name:<25} {short_name:<12} {str(snr):<8} {last_heard_str:<20} {battery_str:<10}")


def main():
    import sys
    config = load_config()
    if "serial_device" not in config:
        print("Error: 'serial_device' not set in config.json")
        sys.exit(1)
    serial_device = config["serial_device"]
    print(f"Connecting to Meshtastic device on {serial_device} ...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=serial_device)
        print("Connected.\n")
        display_nodes(interface)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            interface.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
