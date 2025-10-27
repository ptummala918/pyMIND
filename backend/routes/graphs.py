from fastapi import APIRouter
from backend.services.eeg_service import generate_eeg_live_plot, generate_eeg_trend_plot

router = APIRouter()

@router.get("/eeg/live")
def get_eeg_live_plot():
    return generate_eeg_live_plot()

@router.get("/eeg/trend")
def get_eeg_trend_plot():
    return generate_eeg_trend_plot()

@router.get("/test")
def test_graphs():
    return {"status": "Graphs route working"}
