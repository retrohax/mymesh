import meshtastic
import meshtastic.serial_interface
from meshtastic import mesh_pb2

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
    print("Connecting to Meshtastic device on /dev/ttyUSB1 ...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath="/dev/ttyUSB1")
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
