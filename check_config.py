import json
import os
import meshtastic
import meshtastic.serial_interface

def load_config():
    import sys
    path = os.path.join(os.path.dirname(__file__), "config.json")
    if not os.path.exists(path):
        print(f"Error: config.json not found at {path}")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)

def main():
    import sys
    config = load_config()
    if "serial_device" not in config:
        print("Error: 'serial_device' not set in config.json")
        sys.exit(1)
    serial_device = config["serial_device"]
    print(f"Connecting to {serial_device} ...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=serial_device)

        node = interface.getNode("^local")
        lora = node.localConfig.lora
        print("\n--- LoRa Config ---")
        print(f"  Region:       {lora.region}")
        print(f"  Modem preset: {lora.modem_preset}")
        print(f"  Frequency:    {lora.channel_num} (slot)")
        print(f"  Bandwidth:    {lora.bandwidth}")
        print(f"  Hop limit:    {lora.hop_limit}")

        print("\n--- Channels ---")
        for ch in interface.localNode.channels:
            role = ch.role
            if role == 0:
                continue  # disabled
            settings = ch.settings
            import base64
            psk_b64 = base64.b64encode(settings.psk).decode() if settings.psk else "(none)"
            print(f"  [{ch.index}] name={settings.name!r:15} role={role} psk={psk_b64}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            interface.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
