#!/usr/bin/env python3
"""Generate clean synthetic HDF5 fixtures for pyMIND.

Produces three files that match the exact layout the backend readers expect,
so they can be uploaded through the UI or used in tests:

  synthetic_eeg.hdf5             EEG:      Data (channels x N) + Time (1 x N) + attrs
  synthetic_vitals_waves.hdf5    Waves:    one (2 x N) [time; value] dataset per waveform
  synthetic_vitals_numerics.hdf5 Numerics: one (2 x N) [time; value] dataset per parameter

The signals are intentionally simple (sinusoid-based) but structurally correct:
real sample rates, full length with no zero-padding, and physiologic value
ranges. Times start at one sample period so the backend's `!= 0` validity masks
never drop a real sample.

Usage:
    python tools/generate_synthetic_data.py                 # 5 min, -> SampleData/Synthetic
    python tools/generate_synthetic_data.py --duration 60   # 1 min
    python tools/generate_synthetic_data.py --outdir /tmp/fixtures
"""
import argparse
import os
from datetime import datetime

import h5py
import numpy as np

# --------------------------------------------------------------------------
# EEG
# --------------------------------------------------------------------------
EEG_CHANNELS = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "O1", "O2"]
EEG_FS = 250.0  # Hz


def _time_row(duration: float, fs: float) -> np.ndarray:
    """Time vector in seconds, starting at one sample period (never zero)."""
    n = int(round(duration * fs))
    return (np.arange(1, n + 1, dtype=np.float32) / fs)


def generate_eeg(duration: float, seed: int = 42):
    t = _time_row(duration, EEG_FS)
    n = t.shape[0]
    rng = np.random.default_rng(seed)
    data = np.empty((len(EEG_CHANNELS), n), dtype=np.float32)
    for i in range(len(EEG_CHANNELS)):
        alpha = 30.0 * np.sin(2 * np.pi * 10.0 * t + i)   # ~10 Hz alpha rhythm, ~30 uV
        drift = 5.0 * np.sin(2 * np.pi * 0.3 * t)         # slow baseline drift
        noise = rng.normal(0.0, 4.0, n)                   # background activity
        data[i] = (alpha + drift + noise).astype(np.float32)
    return t.reshape(1, n), data


def write_eeg(path: str, duration: float) -> None:
    time, data = generate_eeg(duration)
    with h5py.File(path, "w") as f:
        f.create_dataset("Time", data=time)
        f.create_dataset("Data", data=data)
        f.attrs["ChannelNames"] = np.array([c.encode("ascii") for c in EEG_CHANNELS], dtype="S8")
        f.attrs["ChannelCount"] = len(EEG_CHANNELS)
        f.attrs["SamplingFreq"] = EEG_FS
        f.attrs["Resolutions"] = np.ones(len(EEG_CHANNELS), dtype=np.float64)  # values already in uV
        f.attrs["InitialTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


# --------------------------------------------------------------------------
# Vitals waveforms
# --------------------------------------------------------------------------
HR_BPM = 75.0
HR_HZ = HR_BPM / 60.0


def _wave_ecg(t: np.ndarray) -> np.ndarray:
    # Spike train that reads as a heartbeat: sharp R peaks + small baseline sway (mV).
    phase = 2 * np.pi * HR_HZ * t
    return (1.2 * np.maximum(np.sin(phase), 0.0) ** 8 - 0.15 * np.sin(phase)).astype(np.float32)


def _wave_abp(t: np.ndarray) -> np.ndarray:
    # Arterial pressure oscillating ~80/120 mmHg at the heart rate.
    return (100.0 + 20.0 * np.sin(2 * np.pi * HR_HZ * t)).astype(np.float32)


def _wave_pleth(t: np.ndarray) -> np.ndarray:
    # Plethysmograph, arbitrary units, in phase with the pulse.
    return (0.5 + 0.5 * np.sin(2 * np.pi * HR_HZ * t)).astype(np.float32)


def _wave_resp(t: np.ndarray) -> np.ndarray:
    # Respiration ~15 breaths/min (0.25 Hz).
    return (0.5 * np.sin(2 * np.pi * 0.25 * t)).astype(np.float32)


# key -> (sample rate Hz, signal function). Keys match the backend's substring matcher.
WAVE_SPECS = {
    "ECG Lead II": (250.0, _wave_ecg),
    "Arterial Blood Pressure (ART)": (125.0, _wave_abp),
    "Pleth": (125.0, _wave_pleth),
    "Imedance RESP wave": (25.0, _wave_resp),
}


def write_vitals_waves(path: str, duration: float) -> None:
    with h5py.File(path, "w") as f:
        for key, (fs, fn) in WAVE_SPECS.items():
            t = _time_row(duration, fs)
            values = fn(t)
            f.create_dataset(key, data=np.vstack([t, values]).astype(np.float32))
        f.attrs["InitialTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


# --------------------------------------------------------------------------
# Vitals numerics (1 Hz)
# --------------------------------------------------------------------------
NUMERICS_FS = 1.0


def generate_numerics(duration: float, seed: int = 7):
    t = _time_row(duration, NUMERICS_FS)
    n = t.shape[0]
    rng = np.random.default_rng(seed)

    def slow(mean, amp, period):
        return mean + amp * np.sin(2 * np.pi * t / period)

    hr = slow(75.0, 3.0, 60.0) + rng.normal(0, 0.5, n)
    spo2 = np.clip(slow(98.0, 0.5, 90.0) + rng.normal(0, 0.2, n), 0, 100)
    sys = slow(120.0, 6.0, 70.0) + rng.normal(0, 0.8, n)
    dia = slow(80.0, 4.0, 70.0) + rng.normal(0, 0.6, n)
    mean = dia + (sys - dia) / 3.0                      # standard MAP estimate
    rr = slow(15.0, 1.0, 80.0) + rng.normal(0, 0.3, n)
    temp = slow(37.0, 0.1, 200.0) + rng.normal(0, 0.02, n)

    # Names chosen to match the backend parameter resolver / threshold panel.
    return {
        "Heart Rate": hr,
        "Arterial Oxigen Saturation": spo2,
        "Arterial Blood Pressure (ART)_MEAN": mean,
        "Arterial Blood Pressure (ART)_SYS": sys,
        "Arterial Blood Pressure (ART)_DIA": dia,
        "Respiration Rate": rr,
        "Unspecific Temperature": temp,
    }, t


def write_vitals_numerics(path: str, duration: float) -> None:
    series, t = generate_numerics(duration)
    with h5py.File(path, "w") as f:
        for key, values in series.items():
            f.create_dataset(key, data=np.vstack([t, values]).astype(np.float32))
        f.attrs["InitialTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


# --------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic pyMIND HDF5 fixtures.")
    parser.add_argument("--duration", type=float, default=300.0,
                        help="Recording length in seconds (default: 300 = 5 min).")
    parser.add_argument("--outdir", default="SampleData/Synthetic",
                        help="Output directory (default: SampleData/Synthetic).")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    eeg = os.path.join(args.outdir, "synthetic_eeg.hdf5")
    waves = os.path.join(args.outdir, "synthetic_vitals_waves.hdf5")
    numerics = os.path.join(args.outdir, "synthetic_vitals_numerics.hdf5")

    write_eeg(eeg, args.duration)
    write_vitals_waves(waves, args.duration)
    write_vitals_numerics(numerics, args.duration)

    print(f"Wrote {args.duration:.0f}s fixtures to {args.outdir}/:")
    for p in (eeg, waves, numerics):
        print(f"  {os.path.basename(p):32s} {os.path.getsize(p) / 1e6:6.2f} MB")


if __name__ == "__main__":
    main()
