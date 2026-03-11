import sys
import time
import json
import os
import meshtastic
import meshtastic.serial_interface

def load_config():
    path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(path):
        print(f"Error: config.json not found at {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)

def main():
    if len(sys.argv) < 2:
        print("Usage: python send_message.py <message>")
        sys.exit(1)

    config = load_config()
    if "serial_device" not in config:
        print("Error: 'serial_device' not set in config.json")
        sys.exit(1)
    serial_device = config["serial_device"]
    message = " ".join(sys.argv[1:])

    print(f"Connecting to {serial_device} ...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=serial_device)
        print(f"Sending: {message!r}")
        interface.sendText(message)
        print("Message sent.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        try:
            interface.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
