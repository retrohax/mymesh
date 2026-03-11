import time
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import json
import os

BROADCAST_ADDR = 0xFFFFFFFF  # "^all" — public broadcast

def load_config(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(path) as f:
        return json.load(f)

def on_receive(packet, interface):
    try:
        decoded = packet.get("decoded", {})
        if decoded.get("portnum") != "TEXT_MESSAGE_APP":
            return  # ignore non-text packets

        to_addr   = packet.get("to", 0)
        from_id   = packet.get("fromId", "unknown")
        message   = decoded.get("text", "")
        channel   = packet.get("channel", 0)

        if to_addr == BROADCAST_ADDR:
            print(f"[PUBLIC ch{channel}] {from_id}: {message}")
        else:
            print(f"[PRIVATE] {from_id} -> {hex(to_addr)}: {message}")

    except Exception as e:
        print(f"Error processing packet: {e}")

def main():
    config = load_config()
    serial_device = config.get("serial_device", "/dev/ttyUSB1")
    print(f"Connecting to {serial_device} ...")
    interface = meshtastic.serial_interface.SerialInterface(devPath=serial_device)
    print("Listening for public messages... (Ctrl+C to stop)\n")

    pub.subscribe(on_receive, "meshtastic.receive.text")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        interface.close()

if __name__ == "__main__":
    main()