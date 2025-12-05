from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import io

router = APIRouter()

# In-memory storage for timestamps (in production, use a database)
timestamps: List[dict] = []


class TimestampCreate(BaseModel):
    time_offset: float
    description: str


class TimestampUpdate(BaseModel):
    description: str


@router.get("/")
def get_all_timestamps():
    """Get all timestamps."""
    return JSONResponse(content={"timestamps": timestamps})


@router.post("/")
def add_timestamp(timestamp: TimestampCreate):
    """Add a new timestamp annotation."""
    new_timestamp = {
        "id": len(timestamps) + 1,
        "time_offset": timestamp.time_offset,
        "description": timestamp.description,
        "created_at": datetime.now().isoformat()
    }
    timestamps.append(new_timestamp)
    return JSONResponse(content={"status": "success", "timestamp": new_timestamp})


@router.put("/{timestamp_id}")
def update_timestamp(timestamp_id: int, timestamp: TimestampUpdate):
    """Update a timestamp's description."""
    for ts in timestamps:
        if ts["id"] == timestamp_id:
            ts["description"] = timestamp.description
            return JSONResponse(content={"status": "success", "timestamp": ts})
    return JSONResponse(content={"status": "error", "message": "Timestamp not found"}, status_code=404)


@router.delete("/{timestamp_id}")
def delete_timestamp(timestamp_id: int):
    """Delete a timestamp."""
    global timestamps
    original_len = len(timestamps)
    timestamps = [ts for ts in timestamps if ts["id"] != timestamp_id]

    if len(timestamps) < original_len:
        return JSONResponse(content={"status": "success"})
    return JSONResponse(content={"status": "error", "message": "Timestamp not found"}, status_code=404)


@router.delete("/")
def clear_all_timestamps():
    """Clear all timestamps."""
    global timestamps
    timestamps = []
    return JSONResponse(content={"status": "success"})


@router.get("/export")
def export_timestamps():
    """Export timestamps as a JSON file."""
    if not timestamps:
        return JSONResponse(content={"status": "error", "message": "No timestamps to export"}, status_code=400)

    export_data = {
        "exported_at": datetime.now().isoformat(),
        "timestamps": timestamps
    }

    # Create a JSON file in memory
    json_str = json.dumps(export_data, indent=2)
    buf = io.BytesIO(json_str.encode('utf-8'))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=timestamps.json"}
    )
