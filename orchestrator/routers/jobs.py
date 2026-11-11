"""
Endpoints de Automações e Execuções (Read-Only no Portão A).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from orchestrator.auth import get_current_user
from orchestrator.config import settings
from orchestrator.services import cloudrun_service

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@router.get("")
async def list_jobs(user: dict = Depends(get_current_user)):
    """Lista todos os Cloud Run Jobs homologados."""
    jobs = cloudrun_service.list_allowed_jobs()
    return {"jobs": jobs, "count": len(jobs)}

@router.get("/executions")
async def list_executions(
    job_name: Optional[str] = Query(None, description="Filtrar por nome do Job"),
    limit: int = Query(30, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Lista o histórico recente de execuções dos robôs."""
    if job_name and not settings.is_job_allowed(job_name):
        raise HTTPException(status_code=403, detail=f"Job '{job_name}' fora da allowlist.")
    executions = cloudrun_service.list_job_executions(job_name=job_name, limit=limit)
    return {"executions": executions, "count": len(executions)}
