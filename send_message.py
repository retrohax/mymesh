import sys
import argparse
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
    parser = argparse.ArgumentParser(description="Send a Meshtastic message.")
    parser.add_argument("message", nargs="+", help="Message text to send")
    parser.add_argument("-t", "--to", dest="destination", metavar="NODE_ID",
                        help="Node ID to send a private message (e.g. !b03df168). Omit for public broadcast.")
    args = parser.parse_args()

    config = load_config()
    if "serial_device" not in config:
        print("Error: 'serial_device' not set in config.json")
        sys.exit(1)
    serial_device = config["serial_device"]
    message = " ".join(args.message)
    destination = args.destination or "^all"

    print(f"Connecting to {serial_device} ...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=serial_device)
        if destination == "^all":
            print(f"Sending public broadcast: {message!r}")
        else:
            print(f"Sending private message to {destination}: {message!r}")
        interface.sendText(message, destinationId=destination)
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
