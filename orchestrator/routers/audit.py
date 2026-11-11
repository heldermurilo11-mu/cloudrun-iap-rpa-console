"""
Endpoints de Consulta à Trilha de Auditoria.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from orchestrator.auth import get_current_user
from orchestrator import audit

router = APIRouter(prefix="/api/audit", tags=["Audit"])

@router.get("")
async def list_audit_events(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Cursor de paginação"),
    user: dict = Depends(get_current_user)
):
    """Consulta histórico de ações administrativas auditadas."""
    events = audit.list_audit_events(limit=limit, start_after=cursor)
    return {"events": events, "count": len(events)}
