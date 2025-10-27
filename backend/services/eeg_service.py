# backend/services/eeg_service.py

import matplotlib
matplotlib.use("Agg")   # ✅ Must come before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
import io
from fastapi.responses import StreamingResponse


def generate_eeg_live_plot():
    """
    Generate a simulated EEG live waveform and return as PNG image.
    """
    time = np.linspace(0, 2, 500)
    freq = 10
    eeg_signal = np.sin(2 * np.pi * freq * time) + 0.2 * np.random.randn(len(time))

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(time, eeg_signal, color='royalblue', linewidth=1.2)
    ax.set_title("EEG Live Signal (Simulated)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude (μV)")
    ax.grid(True, linestyle='--', alpha=0.6)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

def generate_eeg_trend_plot():
    """
    Generate a simulated EEG trend plot (e.g., signal over time window).
    """
    # --- Simulated longer EEG recording ---
    time = np.linspace(0, 60, 3000)  # 1 minute
    freq = 8  # 8 Hz
    eeg_signal = np.sin(2 * np.pi * freq * time) + 0.3 * np.random.randn(len(time))

    # --- Rolling RMS as 'trend' metric ---
    window_size = 200
    trend = np.sqrt(np.convolve(eeg_signal ** 2, np.ones(window_size)/window_size, mode="valid"))

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(time[:len(trend)], trend, color="darkorange", linewidth=1.2)
    ax.set_title("EEG Trend Signal (Simulated)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("RMS Amplitude (μV)")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()

    # --- Convert to PNG ---
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")