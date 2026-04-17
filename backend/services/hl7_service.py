import socket
import threading
import time
from collections import deque
from hl7apy.parser import parse_message
from hl7apy.exceptions import HL7apyException

# MLLP framing characters (RFC 3537 / HL7 MLLP standard)
START_BLOCK = b'\x0b'       # Vertical Tab  (0x0B)
END_BLOCK   = b'\x1c'       # File Separator (0x1C)
CARRIAGE_RETURN = b'\x0d'   # Carriage Return (0x0D)

# ---------------------------------------------------------------------------
# Live data store — written by the HL7 thread, read by the API thread.
# Each parameter keeps a rolling window of (timestamp, value) tuples so the
# frontend can render a time-series, not just the latest scalar.
# ---------------------------------------------------------------------------

_store_lock = threading.Lock()

# Rolling buffer: up to 3600 samples per parameter (~1 hr at 1 Hz)
_BUFFER_SIZE = 3600

_live_numerics: dict[str, deque] = {}   # param_key -> deque of (unix_ts, float)
_live_units:    dict[str, str]   = {}   # param_key -> unit string

# Maps CARESCAPE / HL7 observation identifiers → normalised parameter keys
# The Canvas Smart Display uses GE-proprietary LOINC-style codes and also
# plain text labels in OBX-3.2 (the text component).  We match on both.
_OBX_ID_MAP: dict[str, str] = {
    # ---- Heart Rate ----
    "59408-5":  "HR",   # LOINC pulse ox heart rate
    "8867-4":   "HR",   # LOINC heart rate
    "HR":       "HR",
    "HEART RATE": "HR",
    "PULSE":    "HR",
    # ---- SpO2 ----
    "2708-6":   "SpO2", # LOINC oxygen saturation arterial
    "59408-5":  "SpO2", # (some monitors reuse for SpO2)
    "SPO2":     "SpO2",
    "SP02":     "SpO2",
    "OXYGEN SATURATION": "SpO2",
    "ARTERIAL OXYGEN": "SpO2",
    # ---- Arterial Blood Pressure ----
    "55284-4":  "MAP",  # LOINC ABP mean
    "8478-0":   "MAP",  # LOINC mean BP
    "MAP":      "MAP",
    "MEAN ARTERIAL PRESSURE": "MAP",
    "ABP MEAN": "MAP",
    "ABP-MEAN": "MAP",
    # ---- Systolic / Diastolic (stored separately) ----
    "8480-6":   "SYS",  # LOINC systolic
    "8462-4":   "DIA",  # LOINC diastolic
    "ABP SYS":  "SYS",
    "ABP DIA":  "DIA",
    "SBP":      "SYS",
    "DBP":      "DIA",
    # ---- Respiration Rate ----
    "9279-1":   "RR",   # LOINC respiratory rate
    "RR":       "RR",
    "RESP RATE": "RR",
    "RESPIRATION RATE": "RR",
    # ---- Temperature ----
    "8310-5":   "TEMP", # LOINC body temperature
    "TEMP":     "TEMP",
    "TEMPERATURE": "TEMP",
    # ---- End-tidal CO2 ----
    "19889-5":  "ETCO2",
    "ETCO2":    "ETCO2",
    "ET CO2":   "ETCO2",
    # ---- Intracranial Pressure ----
    "ICP":      "ICP",
    "INTRACRANIAL PRESSURE": "ICP",
    # ---- CVP ----
    "CVP":      "CVP",
    "CENTRAL VENOUS PRESSURE": "CVP",
}


def _resolve_param_key(obs_id: str, obs_text: str) -> str | None:
    """Return normalised parameter key, or None if unknown."""
    for candidate in (obs_id.strip().upper(), obs_text.strip().upper()):
        key = _OBX_ID_MAP.get(candidate)
        if key:
            return key
    return None


def _record(param_key: str, value: float, unit: str, ts: float) -> None:
    """Append a (timestamp, value) sample to the rolling buffer."""
    with _store_lock:
        if param_key not in _live_numerics:
            _live_numerics[param_key] = deque(maxlen=_BUFFER_SIZE)
        _live_numerics[param_key].append((ts, value))
        _live_units[param_key] = unit


def get_live_hl7_data(window_seconds: float = 60.0) -> dict:
    """
    Return the last `window_seconds` of HL7-streamed numeric data.
    Called by the API route; safe to call from any thread.

    Returns:
        {
          "numerics": {
            "HR":   {"time": [...], "values": [...], "unit": "bpm",  "latest": 72},
            "SpO2": {"time": [...], "values": [...], "unit": "%",    "latest": 98},
            ...
          },
          "source": "hl7_live",
          "window_seconds": 60.0
        }
    """
    cutoff = time.time() - window_seconds
    result: dict[str, dict] = {}

    with _store_lock:
        for param, buf in _live_numerics.items():
            window = [(ts, v) for ts, v in buf if ts >= cutoff]
            times  = [ts for ts, _ in window]
            values = [v  for _,  v in window]
            if not times:
                continue
            t0 = times[0]
            result[param] = {
                "time":   [t - t0 for t in times],
                "values": values,
                "unit":   _live_units.get(param, ""),
                "latest": values[-1],
            }

    return {
        "numerics":       result,
        "source":         "hl7_live",
        "window_seconds": window_seconds,
    }


def has_live_hl7_data() -> bool:
    """True if at least one parameter has been received."""
    with _store_lock:
        return bool(_live_numerics)


# ---------------------------------------------------------------------------
# HL7 message handling
# ---------------------------------------------------------------------------

def _build_ack(msg, accept: bool, error_text: str = "") -> bytes:
    """Construct an MLLP-framed ACK or NACK response."""
    msa_code = "AA" if accept else "AE"
    text_field = f"|{error_text}" if error_text else ""
    ack = (
        f"MSH|^~\\&|pyMIND|pyMIND_CLIENT|"
        f"{msg.msh.msh_5.value}|{msg.msh.msh_6.value}|"
        f"{msg.msh.msh_7.value}||ACK^R01|{msg.msh.msh_10.value}|P|2.3\r"
        f"MSA|{msa_code}|{msg.msh.msh_10.value}{text_field}"
    )
    return START_BLOCK + ack.encode("utf-8") + END_BLOCK + CARRIAGE_RETURN


def handle_hl7_message(hl7_data: bytes) -> bytes:
    """
    Parse one complete HL7 message (without MLLP framing bytes).
    Extracts numeric observations and stores them in the live buffer.
    Returns an MLLP-framed ACK or NACK.
    """
    msg = None
    try:
        msg = parse_message(hl7_data.decode("utf-8"), find_groups=False)
        msg_type = msg.msh.msh_9.value
        print(f"[HL7] Message type: {msg_type}  from {msg.msh.msh_3.value}")

        if not hasattr(msg, "obx"):
            return _build_ack(msg, accept=True)

        ts = time.time()

        for obx in msg.obx:
            try:
                obs_id   = obx.obx_3.ce_1.value   # Identifier code
                obs_text = obx.obx_3.ce_2.value    # Text description
                obs_val  = obx.obx_5.value          # Value (string)
                obs_unit = obx.obx_6.ce_1.value     # Unit

                param_key = _resolve_param_key(obs_id, obs_text)
                if param_key is None:
                    print(f"[HL7]   Unknown observation: id={obs_id!r} text={obs_text!r} val={obs_val}")
                    continue

                value = float(obs_val)
                _record(param_key, value, obs_unit, ts)
                print(f"[HL7]   {param_key}: {value} {obs_unit}")

            except (ValueError, AttributeError) as e:
                # Non-numeric or missing field — skip this OBX
                print(f"[HL7]   Skipping OBX segment: {e}")
                continue

        return _build_ack(msg, accept=True)

    except HL7apyException as e:
        print(f"[HL7] Parse error: {e}")
        if msg:
            return _build_ack(msg, accept=False, error_text=str(e))
        # Cannot parse at all — return raw NACK without referencing msg fields
        nack = (
            "MSH|^~\\&|pyMIND|pyMIND_CLIENT|||"
            f"{time.strftime('%Y%m%d%H%M%S')}||ACK^R01|0|P|2.3\r"
            f"MSA|AE|0|{e}"
        )
        return START_BLOCK + nack.encode("utf-8") + END_BLOCK + CARRIAGE_RETURN

    except Exception as e:
        print(f"[HL7] Unexpected error: {e}")
        return b""


# ---------------------------------------------------------------------------
# MLLP server
# ---------------------------------------------------------------------------

def handle_client(conn: socket.socket, addr: tuple) -> None:
    """Receive, frame, parse, and ACK HL7 messages from one MLLP client."""
    data_buffer = b""
    print(f"[HL7] Connection from {addr}")
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data_buffer += chunk

            # Process all complete messages in the buffer
            while START_BLOCK in data_buffer and END_BLOCK in data_buffer:
                start_idx = data_buffer.find(START_BLOCK)
                end_idx   = data_buffer.find(END_BLOCK)

                if end_idx > start_idx:
                    hl7_message = data_buffer[start_idx + 1 : end_idx]

                    print("\n[HL7] --- Raw message ---")
                    print(hl7_message.decode(errors="ignore"))
                    print("[HL7] ----------------")

                    response = handle_hl7_message(hl7_message)
                    if response:
                        conn.sendall(response)

                    # Advance past END_BLOCK (and optional trailing CR)
                    buf_next = end_idx + 1
                    if buf_next < len(data_buffer) and data_buffer[buf_next] == CARRIAGE_RETURN[0]:
                        buf_next += 1
                    data_buffer = data_buffer[buf_next:]
                else:
                    # Malformed frame — discard to recover
                    data_buffer = b""

    except Exception as e:
        print(f"[HL7] Error with {addr}: {e}")
    finally:
        print(f"[HL7] Connection from {addr} closed.")
        conn.close()


def start_mllp_server(host: str = "0.0.0.0", port: int = 6000) -> None:
    """
    Bind a TCP socket and accept MLLP connections indefinitely.
    Each client is handled in its own daemon thread.

    The CARESCAPE Canvas Smart Display must be configured to send HL7 data
    to this machine's IP address on port 6000.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[HL7] MLLP server listening on {host}:{port}")

    while True:
        try:
            conn, addr = server_socket.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except KeyboardInterrupt:
            print("[HL7] Server shutting down.")
            break
        except Exception as e:
            print(f"[HL7] Accept error: {e}")

    server_socket.close()


def start_hl7_listener(host: str = "0.0.0.0", port: int = 6000) -> None:
    """Launch the MLLP server in a background daemon thread."""
    t = threading.Thread(
        target=start_mllp_server,
        args=(host, port),
        name="HL7ListenerThread",
        daemon=True,
    )
    t.start()
