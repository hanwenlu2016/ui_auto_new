from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="UI Automation Platform API")

# CORS Configuration
origins = [
    "http://localhost:5173",  # Vite default port
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to UI Automation Platform API"}

from app.api.v1.api import api_router
from fastapi.staticfiles import StaticFiles
import os

app.include_router(api_router, prefix="/api/v1")

# Mount static files for reports
# reports_dir should be in the backend root directory, not app directory
# main.py is in backend/app/main.py, so we go up two levels to get backend/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
reports_dir = os.path.join(BASE_DIR, "allure-reports")
os.makedirs(reports_dir, exist_ok=True)
app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")
