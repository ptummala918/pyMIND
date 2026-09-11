import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.routes.graphs import router as graph_router
from backend.routes.vitals import router as vitals_router
from backend.routes.timestamps import router as timestamps_router
from backend.services.hl7_service import start_hl7_listener, start_udp_probe, start_tcp_probe

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_hl7_listener()
    # The UDP/TCP port probes are a network-discovery tool used once to find
    # which port a monitor streams on. They bind dozens of ports and log every
    # packet, so they stay off unless explicitly enabled for debugging.
    if os.getenv("PYMIND_DEBUG_PROBE") == "1":
        start_udp_probe()
        start_tcp_probe()
    yield

app = FastAPI(title="pyMIND API", lifespan=lifespan)

# Enable CORS so your frontend (pymind_ui) can talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # open for the static frontend; no cookies are used
    allow_credentials=False,  # "*" origin + credentials is rejected by browsers
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(graph_router, prefix="/api/graphs")
app.include_router(vitals_router, prefix="/api/vitals")
app.include_router(timestamps_router, prefix="/api/timestamps")

@app.get("/")
def root():
    return {"message": "pyMIND backend is running"}