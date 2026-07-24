from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from app.routers import auth, projects, secrets, audit
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NullVault",
    description="A secure secrets and API key management REST API",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(secrets.router)
app.include_router(audit.router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/submit")
def submit_page():
    return FileResponse(STATIC_DIR / "submit.html")


@app.get("/health")
def health():
    return {"status": "ok"}
