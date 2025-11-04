from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import tempfile
import os
from backend.services.eeg_service import generate_eeg_trend_plot, get_eeg_live_data

router = APIRouter()

# Store uploaded file paths temporarily (in production, use proper session management)
uploaded_files = {}

@router.post("/eeg/upload")
async def upload_eeg_file(file: UploadFile = File(...)):
    """Upload an EEG HDF5 file."""
    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="uploads/EEG") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        file_path = tmp_file.name
    
    # Store file path (in production, use session IDs)
    uploaded_files['eeg'] = file_path
    
    return {"status": "File uploaded successfully", "filename": file.filename}

@router.get("/eeg/trend")
def get_eeg_trend_plot():
    file_path = uploaded_files.get('eeg')
    return generate_eeg_trend_plot(file_path)

@router.get("/eeg/live/data")
def get_eeg_live_data_endpoint(time_offset: float = 0.0):
    """
    Get live EEG data as JSON (for canvas rendering).
    
    Args:
        time_offset: Time offset in seconds to scroll through the data (default: 0.0)
    """
    file_path = uploaded_files.get('eeg')
    data = get_eeg_live_data(file_path, time_offset)
    return JSONResponse(content=data)