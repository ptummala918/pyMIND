import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import io
from fastapi.responses import StreamingResponse


def generate_vitals_live_plot():
    """
    Generate a simulated live vitals waveform (e.g., ECG, SpO2, ABP).
    """
    time = np.linspace(0, 5, 1000)
    
    # Simulated ECG waveform
    ecg = 1.5 * np.sin(2 * np.pi * 1.3 * time) + 0.5 * np.sin(2 * np.pi * 10 * time) + 0.1 * np.random.randn(len(time))
    
    # Simulated ABP waveform
    abp = 80 + 20 * np.sin(2 * np.pi * 1.2 * time) + 5 * np.random.randn(len(time))

    # Plot multiple waveforms
    fig, axs = plt.subplots(2, 1, figsize=(8, 4), sharex=True)
    axs[0].plot(time, ecg, color="crimson")
    axs[0].set_title("ECG Lead II (Simulated)")
    axs[0].set_ylabel("Amplitude (mV)")
    axs[1].plot(time, abp, color="royalblue")
    axs[1].set_title("Arterial Blood Pressure (Simulated)")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_ylabel("mmHg")

    for ax in axs:
        ax.grid(True, linestyle="--", alpha=0.6)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

def generate_vitals_trend_plot():
    """
    Generate a simulated vitals trend plot (HR, SpO2, MAP over time).
    """
    time = np.linspace(0, 60, 120)  # 1 minute, 0.5s samples
    hr = 70 + 5 * np.sin(2 * np.pi * time / 30) + np.random.randn(len(time))
    spo2 = 97 + 0.5 * np.sin(2 * np.pi * time / 45) + 0.3 * np.random.randn(len(time))
    map_ = 90 + 8 * np.sin(2 * np.pi * time / 40) + np.random.randn(len(time))

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(time, hr, label="Heart Rate (bpm)", color="crimson")
    ax.plot(time, spo2, label="SpO₂ (%)", color="darkgreen")
    ax.plot(time, map_, label="MAP (mmHg)", color="navy")
    ax.legend(loc="upper right")
    ax.set_title("Vitals Trend (Simulated)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Value")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

