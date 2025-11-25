from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import tempfile
import os
from backend.services.vitals_service import generate_vitals_trend_plot, get_vitals_live_data, get_vitals_numerics_data

router = APIRouter()

# Store uploaded file paths temporarily (in production, use proper session management)
uploaded_files = {}

@router.post("/waves/upload")
async def upload_vitals_waves_file(file: UploadFile = File(...)):
    """Upload a vitals waves HDF5 file."""
    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1]
    os.makedirs("uploads/Vitals", exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="uploads/Vitals") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        file_path = tmp_file.name
    
    # Store file path
    uploaded_files['waves'] = file_path
    
    return {"status": "File uploaded successfully", "filename": file.filename}

@router.post("/numerics/upload")
async def upload_vitals_numerics_file(file: UploadFile = File(...)):
    """Upload a vitals numerics HDF5 file."""
    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1]
    os.makedirs("uploads/Vitals", exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="uploads/Vitals") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        file_path = tmp_file.name
    
    # Store file path
    uploaded_files['numerics'] = file_path
    
    return {"status": "File uploaded successfully", "filename": file.filename}

@router.get("/live/data")
def get_vitals_live_data_endpoint(time_offset: float = 0.0):
    """
    Get live vitals data as JSON (for canvas rendering).
    
    Args:
        time_offset: Time offset in seconds to scroll through the data (default: 0.0)
    """
    waves_file_path = uploaded_files.get('waves')
    numerics_file_path = uploaded_files.get('numerics')
    data = get_vitals_live_data(waves_file_path, numerics_file_path, time_offset)
    return JSONResponse(content=data)

@router.get("/numerics/data")
def get_vitals_numerics_data_endpoint(time_offset: float = 0.0):
    """
    Get vitals numerics data as JSON (for canvas rendering).

    Args:
        time_offset: Time offset in seconds to scroll through the data (default: 0.0)
    """
    file_path = uploaded_files.get('numerics')
    data = get_vitals_numerics_data(file_path, time_offset)
    return JSONResponse(content=data)

@router.get("/trend")
def get_vitals_trend():
    file_path = uploaded_files.get('numerics')
    return generate_vitals_trend_plot(file_path)