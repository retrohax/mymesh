import time
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

BROADCAST_ADDR = 0xFFFFFFFF  # "^all" — public broadcast

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
        # uncomment to also show DMs addressed to your node:
        # else:
        #     print(f"[PRIVATE] {from_id} -> {hex(to_addr)}: {message}")

    except Exception as e:
        print(f"Error processing packet: {e}")

def main():
    print("Connecting to /dev/ttyUSB1 ...")
    interface = meshtastic.serial_interface.SerialInterface(devPath="/dev/ttyUSB1")
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