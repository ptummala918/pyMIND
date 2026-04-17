from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.routes.graphs import router as graph_router
from backend.routes.vitals import router as vitals_router
from backend.routes.timestamps import router as timestamps_router
from backend.services.hl7_service import start_hl7_listener

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the HL7 listener in the background
    start_hl7_listener()
    yield

app = FastAPI(title="pyMIND API", lifespan=lifespan)

# Enable CORS so your frontend (pymind_ui) can talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict to localhost later
    allow_credentials=True,
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