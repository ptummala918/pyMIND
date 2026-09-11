#!/usr/bin/env python3
"""Synthetic HL7/MLLP vitals sender for pyMIND.

Streams ORU^R01 numeric observations to pyMIND's MLLP server exactly the way a
GE CARESCAPE Canvas monitor would, so the live path can be developed and demoed
without the physical device. One message per interval carries HR, SpO2, MAP,
SYS, DIA, RR and TEMP; values come from the same physiologic generator used for
the HDF5 fixtures, and the sender loops over that buffer indefinitely.

Usage:
    # start the backend first (it opens the MLLP server on port 6000):
    #   uvicorn backend.main:app --host 127.0.0.1 --port 8000
    python tools/hl7_sender.py                     # stream to 127.0.0.1:6000, 1 msg/s
    python tools/hl7_sender.py --interval 0.5      # 2 msg/s
    python tools/hl7_sender.py --count 10          # send 10 messages then stop
    python tools/hl7_sender.py --host 172.16.175.81 --port 6000
"""
import argparse
import os
import socket
import sys
import time
from datetime import datetime

# Reuse the physiologic value generator from the fixture tool.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_synthetic_data import generate_numerics

# MLLP framing bytes (must match backend/services/hl7_service.py).
START_BLOCK = b"\x0b"
END_BLOCK = b"\x1c"
CARRIAGE_RETURN = b"\x0d"

# param -> (LOINC code, text label, unit). Codes/labels are chosen to match the
# server's _OBX_ID_MAP so every observation resolves to a known parameter.
OBX_PARAMS = [
    ("hr",   "8867-4", "Heart Rate",             "bpm"),
    ("spo2", "2708-6", "Oxygen Saturation",      "%"),
    ("map",  "8478-0", "Mean Arterial Pressure", "mmHg"),
    ("sys",  "8480-6", "Systolic BP",            "mmHg"),
    ("dia",  "8462-4", "Diastolic BP",           "mmHg"),
    ("rr",   "9279-1", "Respiratory Rate",       "breaths/min"),
    ("temp", "8310-5", "Body Temperature",       "degC"),
]

# Map our short keys to the dataset names produced by generate_numerics().
_SERIES_KEYS = {
    "hr":   "Heart Rate",
    "spo2": "Arterial Oxigen Saturation",
    "map":  "Arterial Blood Pressure (ART)_MEAN",
    "sys":  "Arterial Blood Pressure (ART)_SYS",
    "dia":  "Arterial Blood Pressure (ART)_DIA",
    "rr":   "Respiration Rate",
    "temp": "Unspecific Temperature",
}


def build_oru_message(values: dict, control_id: int) -> str:
    """Build one ORU^R01 message (segments separated by carriage returns)."""
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    segments = [
        f"MSH|^~\\&|CARESCAPE|ICU_BED_01|pyMIND|pyMIND|{now}||ORU^R01|{control_id}|P|2.3",
        "PID|1||SYNTH001||DOE^JANE",
        f"OBR|1||{control_id}|VITALS^Vital Signs|||{now}",
    ]
    for i, (key, code, label, unit) in enumerate(OBX_PARAMS, start=1):
        val = values[key]
        segments.append(
            f"OBX|{i}|NM|{code}^{label}^LN||{val:.1f}|{unit}|||||F"
        )
    return "\r".join(segments)


def frame(message: str) -> bytes:
    """Wrap a message in MLLP framing bytes."""
    return START_BLOCK + message.encode("utf-8") + END_BLOCK + CARRIAGE_RETURN


def read_ack(sock: socket.socket, timeout: float = 5.0) -> str:
    """Read one MLLP-framed ACK and return the raw text (framing stripped)."""
    sock.settimeout(timeout)
    buf = b""
    try:
        while END_BLOCK not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
    except socket.timeout:
        return "(no ACK — timed out)"
    start = buf.find(START_BLOCK)
    end = buf.find(END_BLOCK)
    if start != -1 and end != -1:
        return buf[start + 1:end].decode("utf-8", errors="ignore").replace("\r", " | ")
    return "(no framed ACK received)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream synthetic HL7 vitals to pyMIND's MLLP server.")
    parser.add_argument("--host", default="127.0.0.1", help="MLLP server host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=6000, help="MLLP server port (default: 6000).")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between messages (default: 1.0).")
    parser.add_argument("--count", type=int, default=0, help="Number of messages to send, or 0 for infinite.")
    parser.add_argument("--duration", type=float, default=300.0,
                        help="Length of the physiologic buffer to loop over, in seconds (default: 300).")
    args = parser.parse_args()

    # Pre-compute a physiologic buffer, then loop over it one sample per message.
    series, _t = generate_numerics(args.duration)
    n = len(next(iter(series.values())))

    print(f"[SENDER] Connecting to MLLP server at {args.host}:{args.port} ...")
    try:
        sock = socket.create_connection((args.host, args.port), timeout=5.0)
    except OSError as e:
        print(f"[SENDER] Could not connect: {e}")
        print("[SENDER] Is the backend running? (uvicorn backend.main:app ...)")
        sys.exit(1)

    print(f"[SENDER] Connected. Streaming {'infinite' if args.count == 0 else args.count} "
          f"messages every {args.interval}s. Ctrl+C to stop.")
    sent = 0
    try:
        with sock:
            while args.count == 0 or sent < args.count:
                idx = sent % n
                values = {key: float(series[_SERIES_KEYS[key]][idx]) for key, *_ in OBX_PARAMS}
                message = build_oru_message(values, control_id=sent + 1)
                sock.sendall(frame(message))
                ack = read_ack(sock)
                sent += 1
                print(f"[SENDER] #{sent:<5d} HR={values['hr']:.0f} SpO2={values['spo2']:.0f} "
                      f"MAP={values['map']:.0f}  ACK: {ack}")
                if args.count == 0 or sent < args.count:
                    time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n[SENDER] Stopped after {sent} messages.")
    print(f"[SENDER] Done ({sent} messages sent).")


if __name__ == "__main__":
    main()
