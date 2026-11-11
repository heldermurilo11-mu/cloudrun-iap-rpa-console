"""
Endpoints de Agendamentos (Read-Only no Portão A).
"""
from fastapi import APIRouter, Depends
from orchestrator.auth import get_current_user
from orchestrator.services import scheduler_service

router = APIRouter(prefix="/api/schedulers", tags=["Schedulers"])

@router.get("")
async def list_schedulers(user: dict = Depends(get_current_user)):
    """Lista todos os Cloud Schedulers homologados e seus status."""
    scheds = scheduler_service.list_allowed_schedulers()
    return {"schedulers": scheds, "count": len(scheds)}
