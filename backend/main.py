from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Routers — one import per feature phase
from routers.heat_risk import router as heat_risk_router
from routers.shade_detection import router as shade_router
from routers.vulnerability_map import router as map_router
from routers.budget_optimizer import router as budget_router
from routers.assistant import router as assistant_router
from routers.health_profile import router as health_router
from routers.budget_visualize import router as budget_viz_router

load_dotenv()

app = FastAPI(
    title="ChhayaRakshak AI",
    description="AI-powered Urban Heat Protection System",
    version="1.0.0",
)

# Allow requests from the React dev server
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Feature routers ───────────────────────────────────────────────────────────
app.include_router(heat_risk_router)
app.include_router(shade_router)
app.include_router(map_router)
app.include_router(budget_router)
app.include_router(budget_viz_router)
app.include_router(assistant_router)
app.include_router(health_router)


@app.get("/health", tags=["Status"])
def health_check():
    """Basic health check — confirms the API is running."""
    return {"status": "ok", "message": "ChhayaRakshak AI backend is running"}


@app.get("/", tags=["Status"])
def root():
    return {"message": "Welcome to ChhayaRakshak AI. Visit /docs for API documentation."}
