"""
Servidor FastAPI Principal do GCP RPA Orchestrator.
"""
import os
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from orchestrator.auth import get_current_user
from orchestrator.config import settings
from orchestrator.routers import datapools, jobs, schedulers, logs, audit

app = FastAPI(
    title="Cloud Run RPA Operations Console",
    description="Cloud Run RPA Operations Console (Read-Only Portão A)",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None
)

# CORS seguro
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Headers de Segurança HTTP e CSP Estrito (Zero-CDN)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # CSP Estrito: Permite apenas recursos locais do próprio app ('self')
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self';"
    )
    return response

# Inclusão de Routers API
app.include_router(datapools.router)
app.include_router(jobs.router)
app.include_router(schedulers.router)
app.include_router(logs.router)
app.include_router(audit.router)

# Health Check para Cloud Run
@app.get("/healthz", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "project": settings.GCP_PROJECT_ID,
        "region": settings.GCP_REGION
    }


@app.get("/api/me", tags=["Auth"])
async def get_current_user_profile(user: dict = Depends(get_current_user)):
    """Retorna a identidade e papel do usuário autenticado (Read-Only Portão A)."""
    return {
        "email": user.get("email"),
        "role": user.get("role"),
        "auth_type": user.get("auth_type")
    }

# Montagem de Arquivos Estáticos (Frontend SPA)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_spa():
    """Serve o arquivo index.html da Single Page Application."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(
        status_code=404,
        content={"error": "Frontend SPA index.html não encontrado."}
    )
