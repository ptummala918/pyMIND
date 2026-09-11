# pyMIND: Multimodal Integrated Neurocritical Data

**Version: Beta**

pyMIND is a web-based application for visualizing and analyzing multimodal neurocritical data, including EEG (electroencephalography) and vitals monitoring data. The application provides real-time and trend visualization capabilities for medical professionals and researchers.

## Overview

pyMIND enables users to:
- Upload HDF5 files containing EEG and vitals data
- Visualize real-time data streams with live updating canvas-based graphs
- View trend analysis of historical data
- Monitor multiple channels and waveforms simultaneously

## Features

### Real-Time Visualization
- **EEG Monitoring**: Live canvas-based rendering of EEG channels (up to 8 channels)
  - Real-time scrolling through data with 10-second windows
  - Automatic refresh every 1 second
  - Multi-channel display with individual scaling

- **Vitals Monitoring**: Live canvas-based rendering of vital waveforms
  - ECG (Electrocardiogram)
  - ABP (Arterial Blood Pressure)
  - Pleth (Plethysmography)
  - Resp (Respiration)
  - Real-time scrolling through data with 10-second windows
  - Automatic refresh every 1 second

### Trend Analysis
- **EEG Trends**: Historical trend visualization with rolling RMS calculations
- **Vitals Trends**: Long-term trend analysis of numeric vital signs (HR, SpO₂, MAP)

### File Management
- Upload EEG HDF5 files
- Upload Vitals Waves HDF5 files (for waveform data)
- Upload Vitals Numerics HDF5 files (for trend analysis)
- Automatic graph updates upon file upload

## Project Structure

```
pyMIND/
├── backend/                    # FastAPI backend application
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── routes/                 # API route handlers
│   │   ├── __init__.py
│   │   ├── graphs.py           # EEG-related endpoints
│   │   └── vitals.py           # Vitals-related endpoints
│   │   └── timestamps.py       # Annotation endpoints
│   └── services/               # Business logic services
│       ├── __init__.py
│       ├── eeg_service.py      # EEG data processing
│       ├── vitals_service.py   # Vitals data processing
│       └── hl7_service.py      # Live HL7/MLLP monitor ingestion
│
├── pymind_ui/                  # Frontend web interface
│   ├── py_web.html            # Main HTML interface
│   ├── py_style.css           # Styling
│   └── logo.png               # Brown University logo
│
├── tools/                      # Developer/demo utilities
│   ├── generate_synthetic_data.py  # Make synthetic HDF5 fixtures
│   └── hl7_sender.py               # Stream synthetic live vitals (HL7/MLLP)
│
├── uploads/                    # Uploaded file storage
│   ├── EEG/                   # EEG HDF5 files
│   └── Vitals/                # Vitals HDF5 files
│
├── pyMIND_env/                 # Python virtual environment
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework for building APIs
- **h5py**: HDF5 file reading and processing
- **NumPy**: Numerical computations
- **Matplotlib**: Static image generation for trend plots
- **Uvicorn**: ASGI server

### Frontend
- **HTML5/CSS3**: User interface
- **JavaScript**: Client-side logic
- **Canvas API**: Real-time graph rendering

## Installation

### Prerequisites
- Python 3.9+
- Virtual environment (recommended)

### Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd /path/to/pyMIND
   ```

2. **Activate the virtual environment:**
   ```bash
   source pyMIND_env/bin/activate  # On macOS/Linux
   # or
   pyMIND_env\Scripts\activate     # On Windows
   ```

3. **Install dependencies (if needed):**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Start the Backend Server

```bash
uvicorn backend.main:app --reload
```

The backend will be available at:
- **API Base URL**: `http://127.0.0.1:8000`
- **API Documentation**: `http://127.0.0.1:8000/docs` (Swagger UI)

### Access the Frontend

Open `pymind_ui/py_web.html` in your web browser. The frontend will communicate with the backend API running on `http://127.0.0.1:8000`.

## Demo Without Hardware

pyMIND ships with two developer tools in `tools/` so the entire application —
including the **live monitor connection** — can be run and demoed on a laptop
without an EEG amplifier or a CARESCAPE monitor.

There are two independent data paths; don't confuse them:

| Path | What drives it | Tool |
|---|---|---|
| **File playback** (upload a recording, scroll through it) | HDF5 files you upload in the Visualize tab | `generate_synthetic_data.py` |
| **Live streaming** (real-time monitor feed) | HL7 messages streamed to the backend over the network | `hl7_sender.py` |

### 1. File-playback demo

Generate clean synthetic HDF5 fixtures (5 minutes by default):

```bash
python tools/generate_synthetic_data.py
```

This writes three files to `SampleData/Synthetic/`:
`synthetic_eeg.hdf5`, `synthetic_vitals_waves.hdf5`, `synthetic_vitals_numerics.hdf5`.
Use `--duration <seconds>` for a different length, or `--outdir <path>` to change
where they land.

Then, with the backend running, open the frontend, go to **Visualize**, and
upload each file to its matching slot (EEG / Vitals Waves / Vitals Numerics).
The **Real Time** tab plays the recording back on a scrolling time axis; the
**Trends** tab shows static summary plots.

### 2. Live-streaming demo

The live path needs *something* streaming vitals to the backend's MLLP server
(port `6000`). On a laptop, the synthetic sender stands in for the monitor —
**it does not need the HDF5 files above**; it generates values on the fly.

In one terminal, start the backend (it opens the MLLP server automatically):

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the sender:

```bash
python tools/hl7_sender.py
```

Then in the frontend: **Connect → Vitals → Connect**. Within a second or two the
status flips from amber "waiting for monitor data" to green **"Connected —
receiving"**, and the live numeric readout plus the scrolling strip chart (in the
Visualize tab) come alive. Order doesn't matter — the backend buffers, so you can
start the sender before or after connecting. Stop the sender with `Ctrl+C`.

Useful sender options: `--interval 0.5` (2 messages/sec), `--count 60` (send 60
then stop), `--host` / `--port` (target a different machine).

## API Endpoints

### EEG Endpoints

- `POST /api/graphs/eeg/upload` - Upload EEG HDF5 file
- `GET /api/graphs/eeg/live/data?time_offset={float}` - Get live EEG data as JSON (for canvas rendering)
- `GET /api/graphs/eeg/spectrogram?time_offset={float}&window_duration={float}` - Per-channel spectrogram data
- `GET /api/graphs/eeg/trend` - Get EEG trend plot as PNG image
- `DELETE /api/graphs/eeg/clear` - Clear the uploaded EEG file

### Vitals Endpoints

- `POST /api/vitals/waves/upload` - Upload Vitals Waves HDF5 file
- `POST /api/vitals/numerics/upload` - Upload Vitals Numerics HDF5 file
- `GET /api/vitals/live/data?time_offset={float}` - Get live vitals waveform data as JSON
- `GET /api/vitals/numerics/data?time_offset={float}` - Get vitals numerics data as JSON
- `GET /api/vitals/trend` - Get vitals trend plot as PNG image
- `DELETE /api/vitals/waves/clear` / `DELETE /api/vitals/numerics/clear` - Clear uploaded files

### Live HL7 Endpoints

- `GET /api/vitals/hl7/live?window_seconds={float}` - Rolling window of live numerics (with absolute timestamps)
- `GET /api/vitals/hl7/status` - `{"connected": true/false}` — whether live data has been received

### Annotation Endpoints

- `GET/POST/PUT/DELETE /api/timestamps/` - Manage annotation timestamps
- `GET /api/timestamps/export` - Export annotations as a JSON file

### Root

- `GET /` - Health check endpoint

## Data Format

### EEG HDF5 Files
Expected structure:
- `Time`: 1D array of timestamps
- `Data`: 2D array (channels × samples)

### Vitals Waves HDF5 Files
Expected structure:
- Each dataset contains waveform data:
  - Row 0: Time values
  - Row 1: Signal values
- Supported waveforms: ECG, ABP, Pleth, Resp (identified by key name)

### Vitals Numerics HDF5 Files
Expected structure:
- Each dataset contains numeric vital signs:
  - Row 0: Time values
  - Row 1: Numeric values
- Supported numerics: Heart Rate, SpO₂, MAP, etc.

## Usage

1. **Upload Files**:
   - Navigate to the "Visualize" panel
   - Upload EEG HDF5 file for EEG visualization
   - Upload Vitals Waves HDF5 file for vitals waveform visualization
   - Upload Vitals Numerics HDF5 file for trend analysis

2. **Real-Time View**:
   - Select the "Real Time" tab
   - Graphs automatically update every second
   - Data scrolls through in 10-second windows

3. **Trends View**:
   - Select the "Trends" tab
   - View historical trend analysis
   - Static images generated from uploaded files

## Key Features Implemented

### Real-Time Canvas Rendering
- Both EEG and Vitals graphs use HTML5 Canvas for efficient real-time rendering
- Automatic scrolling through data with configurable time offsets
- Smooth animations and updates

### File Upload Tracking
- Frontend tracks which files have been uploaded
- Graphs only update when corresponding files are available
- Upload status indicators for each file type

## Technical Implementation Details

### Canvas Rendering
- **EEG**: Multi-channel display with individual vertical scaling per channel
- **Vitals**: Multi-waveform display with shared plot area and dual-axis support
- Scientific plotting style with grid, axes, and labels
- Color-coded waveforms for easy identification

### Data Processing
- **Backend**: Reads HDF5 files, extracts time windows based on offset, returns JSON
- **Frontend**: Receives JSON data, renders to canvas with proper scaling
- **Time Windows**: 10-second windows that scroll through the data
- **Refresh Rate**: 1 second intervals with 0.5-second scroll steps

## CARESCAPE Canvas Smart Display — Live HL7 Connection

pyMIND can receive live numeric vitals (HR, SpO₂, MAP, RR, Temp, etc.) directly from a GE CARESCAPE Canvas Smart Display via HL7 v2.x over MLLP (TCP).

### How it works

When the backend starts, it automatically launches an MLLP server on port `6000` that listens for incoming HL7 `ORU^R01` messages from the monitor. Parsed values are stored in a rolling 60-minute buffer and exposed via the `/api/vitals/hl7/live` endpoint.

### Quick-start checklist (do this each session)

**1. Physical connection**
- Plug an Ethernet cable from the monitor's **MC port** into the Mac (via USB-C → Ethernet adapter if needed)
- The IX port is disabled — use MC only

**2. Assign a static IP on the Mac**
- System Settings → Network → select the Ethernet interface
- Details → TCP/IP → Configure IPv4: Manually
- IP Address: `172.16.175.81`
- Subnet Mask: `255.255.255.0`
- Router: (leave blank) → Apply

**3. Verify the link**
```bash
ping 172.16.175.80
```
You should get replies. If you do, the physical link is working.

**4. Start pyMIND**
```bash
cd /Users/praneeth/pyMIND
source pyMIND_env/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
You should see:
```
[HL7] MLLP server listening on 0.0.0.0:6000
```

**5. Confirm data is flowing**
- Watch the terminal for: `[HL7] Connection from ('172.16.175.80', ...)`
- Or check: `http://127.0.0.1:8000/api/vitals/hl7/status` → `{"connected": true}`

**6. One-time biomedical engineering setup (already done once)**
The monitor's HL7 destination IP must be set to `172.16.175.81`, port `6000`, TCP/MLLP. This is locked in the monitor's admin/service menu — only biomedical engineering can set it. Once configured it persists, so this only needs to be done once.

### Network details

| Device | IP | Port |
|---|---|---|
| CARESCAPE Canvas (MC port) | `172.16.175.80` | — |
| This Mac (Ethernet) | `172.16.175.81` | — |
| pyMIND MLLP server | `0.0.0.0` | `6000` |
| pyMIND API | `0.0.0.0` | `8000` |

### Live data API endpoints

| Endpoint | Description |
|---|---|
| `GET /api/vitals/hl7/live?window_seconds=60` | Rolling 60-second window of all numeric parameters |
| `GET /api/vitals/hl7/status` | `{"connected": true/false}` — whether data has been received |

### Parameters received

HR, SpO₂, MAP, SYS, DIA, RR, TEMP, ETCO2, ICP, CVP — matched by both LOINC code and plain-text label from the monitor's OBX segments.

### Troubleshooting

- **Port already in use on startup**: `pkill -9 -f uvicorn` then restart
- **Ping times out but TCP might still work**: some monitors block ICMP — start the backend and watch for the HL7 connection anyway
- **No connection after 60 seconds**: biomedical engineering needs to verify the HL7 destination is set correctly on the monitor
- **No monitor available (development/demo)**: run `python tools/hl7_sender.py` to stream synthetic vitals to the MLLP server — see [Demo Without Hardware](#demo-without-hardware)

---

## Recently Added

- Live vitals connection via the Connect panel (CARESCAPE HL7/MLLP)
- Live scrolling strip chart with a real-time clock axis
- Threshold monitoring with auto-annotation of breaches
- Per-channel EEG spectrograms
- Annotation table with JSON export
- Synthetic data generator and HL7 sender for hardware-free demos

## Future Enhancements

- Live EEG and NIRS acquisition (Connect panel currently supports vitals only)
- Live waveform streaming (HL7 provides numerics only today)
- Session management for multiple concurrent users
- Additional visualization modes and data/graph export

**Note**: This is a beta version. Some features may be under active development.
