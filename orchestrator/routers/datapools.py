"""
Endpoints de Datapools e Filas (Read-Only no Portão A).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from orchestrator.auth import get_current_user
from orchestrator.config import settings
from orchestrator.services import firestore_service

router = APIRouter(prefix="/api/datapools", tags=["Datapools"])

@router.get("")
async def list_datapools(user: dict = Depends(get_current_user)):
    """Lista todos os Datapools homologados disponíveis."""
    pools = firestore_service.list_datapool_collections()
    return {"datapools": pools, "count": len(pools)}

@router.get("/summary")
async def get_dashboard_summary(user: dict = Depends(get_current_user)):
    """Resumo geral de KPIs para o Dashboard."""
    summary = firestore_service.get_dashboard_summary()
    return summary

@router.get("/{datapool_name}/metrics")
async def get_datapool_metrics(datapool_name: str, user: dict = Depends(get_current_user)):
    """Retorna contadores de itens por status para um Datapool."""
    if not settings.is_datapool_allowed(datapool_name):
        raise HTTPException(status_code=403, detail=f"Datapool '{datapool_name}' fora da allowlist.")
    return firestore_service.get_datapool_metrics(datapool_name)

@router.get("/{datapool_name}/items")
async def list_datapool_items(
    datapool_name: str,
    status: Optional[str] = Query(None, description="Filtro de status"),
    search: Optional[str] = Query(None, description="Busca por amostra ou arquivo"),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Cursor de paginação"),
    user: dict = Depends(get_current_user)
):
    """Lista itens de uma fila com paginação e filtros."""
    if not settings.is_datapool_allowed(datapool_name):
        raise HTTPException(status_code=403, detail=f"Datapool '{datapool_name}' fora da allowlist.")
    return firestore_service.list_datapool_items(
        datapool_name=datapool_name,
        status_filter=status,
        search_query=search,
        limit=limit,
        start_after_id=cursor
    )

@router.get("/{datapool_name}/items/{item_id}")
async def get_item_details(datapool_name: str, item_id: str, user: dict = Depends(get_current_user)):
    """Obtém os dados completos de uma amostra na fila."""
    if not settings.is_datapool_allowed(datapool_name):
        raise HTTPException(status_code=403, detail=f"Datapool '{datapool_name}' fora da allowlist.")
    item = firestore_service.get_item_details(datapool_name, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' não encontrado em '{datapool_name}'.")
    return item
