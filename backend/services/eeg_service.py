# backend/services/eeg_service.py

import matplotlib
matplotlib.use("Agg")   # ✅ Must come before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
import io
import h5py
import os
from fastapi.responses import StreamingResponse
from typing import Optional


def read_eeg_hdf5(file_path: str):
    """
    Read EEG data from HDF5 file.
    Returns: (time, data) where time is 1D array and data is (channels, samples)
    """
    with h5py.File(file_path, 'r') as f:
        if 'Time' in f and 'Data' in f:
            time = f['Time'][0, :]  # Get first row, all columns
            data = f['Data'][:, :]  # All channels, all samples
            return time, data
        else:
            raise ValueError("HDF5 file does not contain 'Time' and 'Data' keys")


def get_eeg_live_data(file_path: Optional[str] = None, time_offset: float = 0.0):
    """
    Get EEG data for live display (returns JSON data instead of image).
    Returns dict with channel data.
    """
    window_duration = 10.0  # Show 10 seconds of data at a time
    
    channels = {}
    if file_path and os.path.exists(file_path):
        try:
            time, data = read_eeg_hdf5(file_path)
            
            # Remove zeros and invalid data
            valid_mask = time != 0
            time_valid = time[valid_mask]
            
            if len(time_valid) > 1:
                # Get window of data around time_offset
                start_time = max(time_valid[0], time_valid[0] + time_offset)
                end_time = min(time_valid[-1], start_time + window_duration)
                mask = (time_valid >= start_time) & (time_valid <= end_time)
                
                if np.any(mask):
                    time_window = (time_valid[mask] - start_time).tolist()
                    
                    # Get data for each channel (up to first 8 channels)
                    num_channels = min(data.shape[0], 8)
                    for ch_idx in range(num_channels):
                        channel_data = data[ch_idx, valid_mask]
                        channel_window = channel_data[mask].tolist()
                        channels[f'Channel_{ch_idx + 1}'] = {
                            'time': time_window,
                            'values': channel_window
                        }
        except Exception:
            pass
    
    return {
        'channels': channels,
        'time_offset': time_offset,
        'window_duration': window_duration
    }


def generate_eeg_trend_plot(file_path: Optional[str] = None):
    """
    Generate an EEG trend plot from HDF5 file or simulated data.
    """
    if file_path and os.path.exists(file_path):
        try:
            time, data = read_eeg_hdf5(file_path)
            # Use first channel, calculate rolling RMS
            eeg_signal = data[0, :]
            
            # Calculate rolling RMS as trend metric
            window_size = min(200, len(eeg_signal) // 10)
            if window_size > 1:
                trend = np.sqrt(np.convolve(eeg_signal ** 2, np.ones(window_size)/window_size, mode="valid"))
                time_trend = time[:len(trend)]
            else:
                trend = np.abs(eeg_signal)
                time_trend = time
            
            title = "EEG Trend Signal"
        except Exception as e:
            # Fallback to simulated data
            time_trend = np.linspace(0, 60, 3000)
            freq = 8
            eeg_signal = np.sin(2 * np.pi * freq * time_trend) + 0.3 * np.random.randn(len(time_trend))
            window_size = 200
            trend = np.sqrt(np.convolve(eeg_signal ** 2, np.ones(window_size)/window_size, mode="valid"))
            time_trend = time_trend[:len(trend)]
            title = f"EEG Trend Signal (Error: {str(e)})"
    else:
        # Simulated data
        time_trend = np.linspace(0, 60, 3000)
        freq = 8
        eeg_signal = np.sin(2 * np.pi * freq * time_trend) + 0.3 * np.random.randn(len(time_trend))
        window_size = 200
        trend = np.sqrt(np.convolve(eeg_signal ** 2, np.ones(window_size)/window_size, mode="valid"))
        time_trend = time_trend[:len(trend)]
        title = "EEG Trend Signal (Simulated)"

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(time_trend, trend, color="darkorange", linewidth=1.2)
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("RMS Amplitude (μV)")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")