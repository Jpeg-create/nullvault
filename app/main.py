from fastapi import FastAPI
from app.routers import auth, secrets, audit
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NullVault",
    description="A secure secrets and API key management REST API",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(secrets.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {"status": "ok"}
