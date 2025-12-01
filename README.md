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
│   └── services/               # Business logic services
│       ├── __init__.py
│       ├── eeg_service.py      # EEG data processing
│       ├── vitals_service.py   # Vitals data processing
│       └── utils.py            # Utility functions
│
├── pymind_ui/                  # Frontend web interface
│   ├── py_web.html            # Main HTML interface
│   ├── py_style.css           # Styling
│   └── logo.png               # Brown University logo
│
├── uploads/                    # Uploaded file storage
│   ├── EEG/                   # EEG HDF5 files
│   └── Vitals/                # Vitals HDF5 files
│
├── pyMINDenv/                  # Python virtual environment
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
   source pyMINDenv/bin/activate  # On macOS/Linux
   # or
   pyMINDenv\Scripts\activate     # On Windows
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

## API Endpoints

### EEG Endpoints

- `POST /api/graphs/eeg/upload` - Upload EEG HDF5 file
- `GET /api/graphs/eeg/live/data?time_offset={float}` - Get live EEG data as JSON (for canvas rendering)
- `GET /api/graphs/eeg/trend` - Get EEG trend plot as PNG image

### Vitals Endpoints

- `POST /api/vitals/waves/upload` - Upload Vitals Waves HDF5 file
- `POST /api/vitals/numerics/upload` - Upload Vitals Numerics HDF5 file
- `GET /api/vitals/live/data?time_offset={float}` - Get live vitals data as JSON (for canvas rendering)
- `GET /api/vitals/trend` - Get vitals trend plot as PNG image

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

## Future Enhancements

- Connect panel functionality for real-time data acquisition
- Disconnect panel functionality for managing active connections
- Timestamp table for adding annotations
- Additional visualization modes
- Export functionality for graphs and data
- Session management for multiple users

**Note**: This is a beta version. Some features may be under active development.
