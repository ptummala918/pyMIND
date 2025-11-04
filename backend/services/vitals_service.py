import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import io
import h5py
import os
from fastapi.responses import StreamingResponse
from typing import Optional


def read_vitals_waves_hdf5(file_path: str):
    """
    Read vitals waveform data from HDF5 file.
    Returns: dict with waveform names as keys and (time, values) tuples as values
    """
    waves = {}
    with h5py.File(file_path, 'r') as f:
        for key in f.keys():
            if isinstance(f[key], h5py.Dataset):
                data = f[key][:]
                if data.shape[0] >= 2:
                    time = data[0, :]
                    values = data[1, :]
                    waves[key] = (time, values)
    return waves


def read_vitals_numerics_hdf5(file_path: str):
    """
    Read vitals numeric data from HDF5 file.
    Returns: dict with parameter names as keys and (time, values) tuples as values
    """
    numerics = {}
    with h5py.File(file_path, 'r') as f:
        for key in f.keys():
            if isinstance(f[key], h5py.Dataset):
                data = f[key][:]
                if data.shape[0] >= 2:
                    time = data[0, :]
                    values = data[1, :]
                    numerics[key] = (time, values)
    return numerics


def get_vitals_live_data(waves_file_path: Optional[str] = None, numerics_file_path: Optional[str] = None, time_offset: float = 0.0):
    """
    Get vitals data for live display (returns JSON data instead of image).
    Returns dict with waveforms and numeric values.
    """
    window_duration = 10.0  # Show 10 seconds of data at a time
    
    # Read waveforms
    waveforms = {}
    if waves_file_path and os.path.exists(waves_file_path):
        try:
            waves = read_vitals_waves_hdf5(waves_file_path)
            
            # Find available waveforms
            ecg_key = None
            abp_key = None
            pleth_key = None
            resp_key = None
            
            for key in waves.keys():
                key_lower = key.lower()
                if 'ecg' in key_lower:
                    ecg_key = key
                elif 'abp' in key_lower or 'arterial' in key_lower or 'art' in key_lower:
                    abp_key = key
                elif 'pleth' in key_lower:
                    pleth_key = key
                elif 'resp' in key_lower or 'impedance' in key_lower:
                    resp_key = key
            
            # Get ECG data
            if ecg_key:
                time_ecg_full, ecg_full = waves[ecg_key]
                valid_mask = time_ecg_full != 0
                time_ecg_full = time_ecg_full[valid_mask]
                ecg_full = ecg_full[valid_mask]
                
                if len(time_ecg_full) > 1:
                    start_time = max(time_ecg_full[0], time_ecg_full[0] + time_offset)
                    end_time = min(time_ecg_full[-1], start_time + window_duration)
                    mask = (time_ecg_full >= start_time) & (time_ecg_full <= end_time)
                    time_ecg = (time_ecg_full[mask] - start_time).tolist()
                    ecg = ecg_full[mask].tolist()
                    waveforms['ecg'] = {'time': time_ecg, 'values': ecg, 'label': ecg_key}
            
            # Get ABP data
            if abp_key:
                time_abp_full, abp_full = waves[abp_key]
                valid_mask = time_abp_full != 0
                time_abp_full = time_abp_full[valid_mask]
                abp_full = abp_full[valid_mask]
                
                if len(time_abp_full) > 1:
                    start_time = max(time_abp_full[0], time_abp_full[0] + time_offset)
                    end_time = min(time_abp_full[-1], start_time + window_duration)
                    mask = (time_abp_full >= start_time) & (time_abp_full <= end_time)
                    time_abp = (time_abp_full[mask] - start_time).tolist()
                    abp = abp_full[mask].tolist()
                    waveforms['abp'] = {'time': time_abp, 'values': abp, 'label': abp_key}
            
            # Get Pleth data if available
            if pleth_key:
                time_pleth_full, pleth_full = waves[pleth_key]
                valid_mask = time_pleth_full != 0
                time_pleth_full = time_pleth_full[valid_mask]
                pleth_full = pleth_full[valid_mask]
                
                if len(time_pleth_full) > 1:
                    start_time = max(time_pleth_full[0], time_pleth_full[0] + time_offset)
                    end_time = min(time_pleth_full[-1], start_time + window_duration)
                    mask = (time_pleth_full >= start_time) & (time_pleth_full <= end_time)
                    time_pleth = (time_pleth_full[mask] - start_time).tolist()
                    pleth = pleth_full[mask].tolist()
                    waveforms['pleth'] = {'time': time_pleth, 'values': pleth, 'label': pleth_key}
            
            # Get Resp data if available
            if resp_key:
                time_resp_full, resp_full = waves[resp_key]
                valid_mask = time_resp_full != 0
                time_resp_full = time_resp_full[valid_mask]
                resp_full = resp_full[valid_mask]
                
                if len(time_resp_full) > 1:
                    start_time = max(time_resp_full[0], time_resp_full[0] + time_offset)
                    end_time = min(time_resp_full[-1], start_time + window_duration)
                    mask = (time_resp_full >= start_time) & (time_resp_full <= end_time)
                    time_resp = (time_resp_full[mask] - start_time).tolist()
                    resp = resp_full[mask].tolist()
                    waveforms['resp'] = {'time': time_resp, 'values': resp, 'label': resp_key}
            
        except Exception as e:
            pass
    
    # Convert waveforms to a format suitable for plotting
    # Use waveforms as the primary data source for vitals graphs
    waveforms_series = {}
    for key, waveform_data in waveforms.items():
        waveforms_series[key] = {
            'time': waveform_data['time'],
            'values': waveform_data['values']
        }
    
    return {
        'waveforms': waveforms,
        'waveforms_series': waveforms_series,
        'time_offset': time_offset,
        'window_duration': window_duration
    }


def generate_vitals_trend_plot(numerics_file_path: Optional[str] = None):
    """
    Generate a vitals trend plot from HDF5 file or simulated data.
    """
    if numerics_file_path and os.path.exists(numerics_file_path):
        try:
            numerics = read_vitals_numerics_hdf5(numerics_file_path)
            
            # Find HR, SpO2, and MAP
            hr_key = None
            spo2_key = None
            map_key = None
            
            for key in numerics.keys():
                if 'Heart Rate' in key or 'HR' in key:
                    hr_key = key
                if 'SpO2' in key or 'Oxigen Saturation' in key or 'Arterial Oxigen' in key:
                    spo2_key = key
                if 'MAP' in key or 'MEAN' in key:
                    map_key = key
            
            # Get data
            if hr_key:
                time_hr, hr = numerics[hr_key]
                # Remove zeros
                mask = hr != 0
                time_hr = time_hr[mask]
                hr = hr[mask]
            else:
                time_hr = np.linspace(0, 60, 120)
                hr = 70 + 5 * np.sin(2 * np.pi * time_hr / 30) + np.random.randn(len(time_hr))
            
            if spo2_key:
                time_spo2, spo2 = numerics[spo2_key]
                mask = spo2 != 0
                time_spo2 = time_spo2[mask]
                spo2 = spo2[mask]
            else:
                time_spo2 = np.linspace(0, 60, 120)
                spo2 = 97 + 0.5 * np.sin(2 * np.pi * time_spo2 / 45) + 0.3 * np.random.randn(len(time_spo2))
            
            if map_key:
                time_map, map_ = numerics[map_key]
                mask = map_ != 0
                time_map = time_map[mask]
                map_ = map_[mask]
            else:
                time_map = np.linspace(0, 60, 120)
                map_ = 90 + 8 * np.sin(2 * np.pi * time_map / 40) + np.random.randn(len(time_map))
            
            title = "Vitals Trend"
            
        except Exception as e:
            # Fallback to simulated data
            time_hr = np.linspace(0, 60, 120)
            hr = 70 + 5 * np.sin(2 * np.pi * time_hr / 30) + np.random.randn(len(time_hr))
            time_spo2 = np.linspace(0, 60, 120)
            spo2 = 97 + 0.5 * np.sin(2 * np.pi * time_spo2 / 45) + 0.3 * np.random.randn(len(time_spo2))
            time_map = np.linspace(0, 60, 120)
            map_ = 90 + 8 * np.sin(2 * np.pi * time_map / 40) + np.random.randn(len(time_map))
            title = f"Vitals Trend (Error: {str(e)})"
    else:
        # Simulated data
        time_hr = np.linspace(0, 60, 120)
        hr = 70 + 5 * np.sin(2 * np.pi * time_hr / 30) + np.random.randn(len(time_hr))
        time_spo2 = np.linspace(0, 60, 120)
        spo2 = 97 + 0.5 * np.sin(2 * np.pi * time_spo2 / 45) + 0.3 * np.random.randn(len(time_spo2))
        time_map = np.linspace(0, 60, 120)
        map_ = 90 + 8 * np.sin(2 * np.pi * time_map / 40) + np.random.randn(len(time_map))
        title = "Vitals Trend (Simulated)"

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(time_hr, hr, label="Heart Rate (bpm)", color="crimson")
    ax.plot(time_spo2, spo2, label="SpO₂ (%)", color="darkgreen")
    ax.plot(time_map, map_, label="MAP (mmHg)", color="navy")
    ax.legend(loc="upper right")
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Value")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")