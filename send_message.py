import sys
import time
import meshtastic
import meshtastic.serial_interface

DEVICE = "/dev/ttyUSB1"

def main():
    if len(sys.argv) < 2:
        print("Usage: python send_message.py <message>")
        sys.exit(1)

    message = " ".join(sys.argv[1:])

    print(f"Connecting to {DEVICE} ...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=DEVICE)
        print(f"Sending: {message!r}")
        interface.sendText(message)
        time.sleep(3)   # allow radio time to transmit before closing
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
