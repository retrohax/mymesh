import meshtastic
import meshtastic.serial_interface
from meshtastic import mesh_pb2
import json
import os

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {config_path}. Using default settings.")
        return {}
    except json.JSONDecodeError:
        print(f"Error parsing config file at {config_path}. Using default settings.")
        return {}

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
        last_heard = node.get("lastHeard", "N/A")
        battery    = metrics.get("batteryLevel", "N/A")
        battery_str = f"{battery}%" if isinstance(battery, (int, float)) else str(battery)

        print(f"{node_id:<12} {long_name:<25} {short_name:<12} {str(snr):<8} {str(last_heard):<20} {battery_str:<10}")


def main():
    config = load_config()
    serial_device = config.get("serial_device", "/dev/ttyUSB1")
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
