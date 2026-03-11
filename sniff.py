#!/usr/bin/env python3
"""
Meshtastic LoRa promiscuous sniffer decoder.

Reads binary frames from a RadioLib-flashed sniffer device (src/main.cpp),
decrypts with the Meshtastic default channel key, and prints plaintext
messages to stdout.

Frame format from sniffer:
    b"PKT"  - 3-byte magic
    length  - 2 bytes big-endian
    payload - <length> bytes (PacketHeader[16] + encrypted Data protobuf)
    rssi    - 4 bytes little-endian float
    snr     - 4 bytes little-endian float

PacketHeader layout (16 bytes, all little-endian):
    uint32 to
    uint32 from
    uint32 id
    uint32 flags:8 | channel:8 | next_hop:8 | relay_node:8

AES-128-CTR key (Meshtastic default channel, PSK=0x01):
    Source: firmware/src/mesh/Channels.h defaultpsk[]

CTR nonce (16 bytes):
    bytes  0-7:  packet_id as uint64 LE (zero-extended from uint32)
    bytes  8-11: from_node as uint32 LE
    bytes 12-15: counter (starts at 0, increments LE — matches Arduino Crypto CTR)

Usage:
    python sniff.py
"""

import json
import struct
import sys
import time
from collections import deque
from datetime import datetime

import serial
from Crypto.Cipher import AES
from Crypto.Util import Counter
from meshtastic import mesh_pb2, telemetry_pb2

# ---------------------------------------------------------------------------
# Meshtastic default channel AES-128 key (PSK index 1, "AQ==")
# Source: firmware/src/mesh/Channels.h, defaultpsk[]
# ---------------------------------------------------------------------------
DEFAULT_KEY = bytes([
    0xd4, 0xf1, 0xbb, 0x3a, 0x20, 0x29, 0x07, 0x59,
    0xf0, 0xbc, 0xff, 0xab, 0xcf, 0x4e, 0x69, 0x01,
])

PACKET_HEADER_SIZE = 16

# Meshtastic PortNum values (mesh.proto)
TEXT_MESSAGE_APP = 1
POSITION_APP     = 3
NODEINFO_APP     = 4
TELEMETRY_APP    = 67
TRACEROUTE_APP    = 70


def load_config():
    try:
        with open("config.json") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print("ERROR: config.json not found", file=sys.stderr)
        sys.exit(1)
    if "sniffer_device" not in cfg:
        print("ERROR: 'sniffer_device' key missing from config.json", file=sys.stderr)
        sys.exit(1)
    return cfg


def decrypt_payload(ciphertext: bytes, packet_id: int, from_node: int,
                    key: bytes = DEFAULT_KEY) -> bytes:
    """AES-CTR decrypt matching Meshtastic's CryptoEngine / Arduino Crypto CTR."""
    # Nonce prefix: packet_id (8 bytes LE) + from_node (4 bytes LE) = 12 bytes
    nonce_prefix = struct.pack("<Q", packet_id) + struct.pack("<I", from_node)
    # Arduino Crypto CTR increments the counter starting from the first (LSB)
    # byte of the counter portion → little_endian=True in pycryptodome.
    ctr = Counter.new(32, prefix=nonce_prefix, initial_value=0, little_endian=True)
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
    return cipher.decrypt(ciphertext)


def read_frame(ser: serial.Serial):
    """
    Block until a complete 'PKT' frame is read from the sniffer.
    Returns (payload_bytes, rssi_float, snr_float).
    Handles sync loss by scanning byte-by-byte for the magic.
    """
    while True:
        # Scan for 'P'
        b = ser.read(1)
        if b != b"P":
            continue
        rest = ser.read(2)
        if rest != b"KT":
            # If 'P' is in what we just read, loop will re-find it
            continue

        # Read 2-byte big-endian length
        raw_len = ser.read(2)
        if len(raw_len) < 2:
            continue
        length = struct.unpack(">H", raw_len)[0]
        if length < PACKET_HEADER_SIZE or length > 256:
            continue

        payload = ser.read(length)
        if len(payload) < length:
            continue

        meta = ser.read(8)
        if len(meta) < 8:
            continue

        rssi = struct.unpack("<f", meta[:4])[0]
        snr  = struct.unpack("<f", meta[4:])[0]
        return payload, rssi, snr


def decode_packet(payload: bytes) -> dict | None:
    """
    Parse PacketHeader and attempt to decrypt + decode the Data protobuf.
    Returns a dict with packet fields on success, or None if decode fails.
    """
    if len(payload) < PACKET_HEADER_SIZE:
        return None

    to, from_, packet_id, flags_word = struct.unpack_from("<IIII", payload, 0)
    channel = (flags_word >> 8) & 0xFF

    ciphertext = payload[PACKET_HEADER_SIZE:]
    if not ciphertext:
        return None

    decrypted = decrypt_payload(ciphertext, packet_id, from_)

    try:
        data = mesh_pb2.Data()
        data.ParseFromString(decrypted)
        # Reject obviously-garbage results: portnum must be a valid small integer
        if data.portnum < 0 or data.portnum > 512:
            return None
    except Exception:
        return None

    return {
        "to":        to,
        "from":      from_,
        "packet_id": packet_id,
        "channel":   channel,
        "portnum":   data.portnum,
        "payload":   bytes(data.payload),
    }


def fmt_node(node_id: int) -> str:
    if node_id == 0xFFFFFFFF:
        return "^all"
    return f"!{node_id:08x}"


def main():
    cfg = load_config()
    device = cfg["sniffer_device"]

    print(f"Opening sniffer on {device} …", file=sys.stderr)
    try:
        ser = serial.Serial(device, 921600, timeout=5)
    except serial.SerialException as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("Listening for Meshtastic LONG_FAST US packets …", file=sys.stderr)

    # Deduplicate relay copies — Meshtastic preserves original (from, packet_id)
    seen = deque(maxlen=64)

    while True:
        try:
            payload, rssi, snr = read_frame(ser)
        except serial.SerialException as e:
            print(f"ERROR: serial read failed: {e}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nStopped.", file=sys.stderr)
            break

        pkt = decode_packet(payload)
        if pkt is None:
            # Encrypted with a different key (different channel/PSK), skip silently
            continue

        dedup_key = (pkt["from"], pkt["packet_id"])
        if dedup_key in seen:
            continue
        seen.append(dedup_key)

        portnum = pkt["portnum"]
        src = fmt_node(pkt["from"])
        dst = fmt_node(pkt["to"])
        meta = f"[RSSI {rssi:.0f} dBm  SNR {snr:.1f} dB]"

        if portnum == TEXT_MESSAGE_APP:
            try:
                text = pkt["payload"].decode("utf-8")
            except UnicodeDecodeError:
                text = repr(pkt["payload"])
            print(f"{src} → {dst}  {meta}  {text}")
        elif portnum == POSITION_APP:
            try:
                pos = mesh_pb2.Position()
                pos.ParseFromString(pkt["payload"])
                lat  = pos.latitude_i  / 1e7
                lon  = pos.longitude_i / 1e7
                alt  = f"  alt {pos.altitude}m" if pos.altitude else ""
                print(f"{src} → {dst}  {meta}  pos {lat:.6f},{lon:.6f}{alt}")
            except Exception:
                print(f"{src} → {dst}  {meta}  portnum={portnum}  "
                      f"payload={pkt['payload'].hex()}")
        elif portnum == NODEINFO_APP:
            try:
                user = mesh_pb2.User()
                user.ParseFromString(pkt["payload"])
                parts = []
                if user.long_name:  parts.append(user.long_name)
                if user.short_name: parts.append(f"({user.short_name})")
                if user.hw_model:   parts.append(f"hw={user.hw_model}")
                if user.is_licensed: parts.append("licensed")
                print(f"{src} → {dst}  {meta}  nodeinfo {' '.join(parts)}")
            except Exception:
                print(f"{src} → {dst}  {meta}  portnum={portnum}  "
                      f"payload={pkt['payload'].hex()}")
        elif portnum == TELEMETRY_APP:
            try:
                tel = telemetry_pb2.Telemetry()
                tel.ParseFromString(pkt["payload"])
                dm = tel.device_metrics
                parts = []
                if dm.battery_level:       parts.append(f"batt={dm.battery_level}%")
                if dm.voltage:             parts.append(f"{dm.voltage:.2f}V")
                if dm.channel_utilization: parts.append(f"ch_util={dm.channel_utilization:.1f}%")
                if dm.air_util_tx:         parts.append(f"air_tx={dm.air_util_tx:.1f}%")
                print(f"{src} → {dst}  {meta}  telemetry {' '.join(parts) if parts else '(no device metrics)'}")
            except Exception:
                print(f"{src} → {dst}  {meta}  portnum={portnum}  "
                      f"payload={pkt['payload'].hex()}")
        elif portnum == TRACEROUTE_APP:
            try:
                route = mesh_pb2.RouteDiscovery()
                route.ParseFromString(pkt["payload"])
                hops = [f"!{n:08x}" for n in route.route]
                hops_back = [f"!{n:08x}" for n in route.route_back]
                if hops or hops_back:
                    fwd = " → ".join([src] + hops + [dst]) if hops else f"{src} → {dst}"
                    back = " → ".join(hops_back) if hops_back else ""
                    route_str = fwd + (f"  (back: {back})" if back else "")
                else:
                    route_str = f"{src} → {dst}  (request, no hops yet)"
                print(f"{src} → {dst}  {meta}  traceroute {route_str}")
            except Exception:
                print(f"{src} → {dst}  {meta}  portnum={portnum}  "
                      f"payload={pkt['payload'].hex()}")
        else:
            print(f"{src} → {dst}  {meta}  portnum={portnum}  "
                  f"payload={pkt['payload'].hex()}")


if __name__ == "__main__":
    main()
