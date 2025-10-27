from fastapi import APIRouter
from backend.services.vitals_service import generate_vitals_live_plot, generate_vitals_trend_plot

router = APIRouter()

@router.get("/live")
def get_vitals_live():
    return generate_vitals_live_plot()

@router.get("/trend")
def get_vitals_trend():
    return generate_vitals_trend_plot()

@router.get("/test")
def test_vitals():
    return {"status": "Vitals route working"}
