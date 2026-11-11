"""
Endpoints de Consulta a Logs Estruturados no Cloud Logging.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from orchestrator.auth import get_current_user
from orchestrator.services import logging_service

router = APIRouter(prefix="/api/logs", tags=["Logs"])

@router.get("")
async def list_logs(
    severity: Optional[str] = Query(None, description="Filtro de severidade (INFO, WARNING, ERROR)"),
    job_name: Optional[str] = Query(None, description="Filtro por nome do Job"),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """Consulta logs estruturados no Google Cloud Logging."""
    logs = logging_service.list_logs(severity=severity, job_name=job_name, limit=limit)
    return {"logs": logs, "count": len(logs)}
