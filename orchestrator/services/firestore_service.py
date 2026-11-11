"""
Serviço de consulta e gestão de Datapools no Cloud Firestore.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from google.cloud import firestore
from orchestrator.config import settings

logger = logging.getLogger("orchestrator.firestore")

_db: Optional[firestore.Client] = None
_metrics_cache: Dict[str, Dict[str, Any]] = {}

def get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(
            project=settings.GCP_PROJECT_ID,
            database=settings.FIRESTORE_DATABASE
        )
    return _db

def list_datapool_collections() -> List[str]:
    """
    Lista coleções de datapool homologadas conforme a allowlist.
    """
    try:
        db = get_db()
        # No Firestore nativo, collections() lista coleções na raiz
        collections = db.collections()
        allowed = []
        for col in collections:
            col_id = col.id
            if settings.is_datapool_allowed(col_id):
                allowed.append(col_id)
        
        # Também verifica se há subcoleções sob a raiz 'datapools'
        try:
            root_dps = db.collection("datapools").document("active_pools").get()
            if root_dps.exists:
                pool_list = root_dps.to_dict().get("list", [])
                for p in pool_list:
                    if settings.is_datapool_allowed(p) and p not in allowed:
                        allowed.append(p)
        except Exception:
            pass
            
        return sorted(allowed, reverse=True)
    except Exception as e:
        logger.error(f"Erro ao listar coleções de datapool: {e}")
        return []

def get_datapool_metrics(datapool_name: str) -> Dict[str, Any]:
    """
    Obtém contadores agregados por status com cache em memória (TTL curto).
    """
    if not settings.is_datapool_allowed(datapool_name):
        raise ValueError(f"Datapool '{datapool_name}' não está na lista de recursos permitidos.")
        
    global _metrics_cache
    now = time.time()
    cached = _metrics_cache.get(datapool_name)
    if cached and (now - cached.get("timestamp", 0)) < settings.CACHE_TTL_SECONDS:
        return cached.get("data", {})
        
    try:
        db = get_db()
        pool_ref = db.collection("datapools").document(datapool_name)
        items_ref = pool_ref.collection("items")
        metadata = pool_ref.get().to_dict() or {}
        
        counts = {
            "QUEUED": 0,
            "PROCESSING": 0,
            "DONE": 0,
            "FAILED": 0,
            "TIMEOUT": 0,
            "CANCELED": 0,
            "TOTAL": 0
        }
        
        if metadata.get("counters_version") == 1:
            stored = metadata.get("counts", {})
            counts = {status: int(stored.get(status, 0)) for status in counts}
            if any(value < 0 for value in counts.values()) or counts["TOTAL"] != sum(
                    value for status, value in counts.items() if status != "TOTAL"):
                raise ValueError("Contadores inconsistentes; reconciliacao necessaria")
        else:
            # Legacy queues use server-side aggregates, never a document scan.
            counts["TOTAL"] = items_ref.count().get()[0][0].value
            for status in ("PROCESSING", "DONE", "FAILED", "TIMEOUT", "CANCELED"):
                query = items_ref.where(filter=firestore.FieldFilter("status", "==", status))
                counts[status] = query.count().get()[0][0].value
            counts["QUEUED"] = counts["TOTAL"] - sum(counts[status] for status in (
                "PROCESSING", "DONE", "FAILED", "TIMEOUT", "CANCELED"))
            
        success_rate = (counts["DONE"] / counts["TOTAL"] * 100) if counts["TOTAL"] > 0 else 100.0
        
        result = {
            "datapool": datapool_name,
            "counts": counts,
            "success_rate": round(success_rate, 1),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        _metrics_cache[datapool_name] = {
            "timestamp": now,
            "data": result
        }
        return result
    except Exception as e:
        logger.error(f"Erro ao calcular métricas do datapool '{datapool_name}': {e}")
        return {
            "datapool": datapool_name,
            "counts": {"QUEUED": 0, "PROCESSING": 0, "DONE": 0, "FAILED": 0, "TIMEOUT": 0, "CANCELED": 0, "TOTAL": 0},
            "success_rate": 0.0,
            "error": str(e)
        }

def list_datapool_items(
    datapool_name: str,
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 50,
    start_after_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lista itens da fila com paginação segura e filtros.
    """
    if not settings.is_datapool_allowed(datapool_name):
        raise ValueError(f"Datapool '{datapool_name}' não está na lista de recursos permitidos.")
        
    try:
        db = get_db()
        items_ref = db.collection("datapools").document(datapool_name).collection("items")
        
        query = items_ref.order_by("created_at", direction=firestore.Query.DESCENDING)
        
        if status_filter and status_filter.upper() != "ALL":
            query = query.where("status", "==", status_filter.upper())
            
        query = query.limit(min(limit, settings.PAGE_SIZE_LIMIT))
        
        if start_after_id:
            last_doc = items_ref.document(start_after_id).get()
            if last_doc.exists:
                query = query.start_after(last_doc)
                
        docs = query.stream()
        items = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            
            # Filtro de busca textual local (código da amostra ou nome de arquivo)
            if search_query:
                q = search_query.lower()
                sample_ref = str(d.get("sample_ref", "")).lower()
                file_name = str(d.get("file_name", "")).lower()
                doc_id = str(doc.id).lower()
                if q not in sample_ref and q not in file_name and q not in doc_id:
                    continue
                    
            items.append(d)
            
        return {
            "datapool": datapool_name,
            "items": items,
            "count": len(items),
            "next_cursor": items[-1]["id"] if len(items) == limit else None
        }
    except Exception as e:
        logger.error(f"Erro ao listar itens de '{datapool_name}': {e}")
        return {"datapool": datapool_name, "items": [], "count": 0, "error": str(e)}

def get_item_details(datapool_name: str, item_id: str) -> Optional[Dict[str, Any]]:
    """Obtém os detalhes completos de uma amostra na fila."""
    if not settings.is_datapool_allowed(datapool_name):
        raise ValueError(f"Datapool '{datapool_name}' não está na lista de recursos permitidos.")
        
    try:
        db = get_db()
        doc = db.collection("datapools").document(datapool_name).collection("items").document(item_id).get()
        if doc.exists:
            d = doc.to_dict()
            d["id"] = doc.id
            return d
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar item '{item_id}' em '{datapool_name}': {e}")
        return None

def get_dashboard_summary() -> Dict[str, Any]:
    """Calcula o resumo geral para o Dashboard principal."""
    try:
        pools = list_datapool_collections()
        total_queued = 0
        total_processing = 0
        total_done = 0
        total_failed = 0
        total_items = 0
        
        pool_summaries = []
        for p in pools[:5]:  # Primeiros 5 datapools mais recentes
            m = get_datapool_metrics(p)
            counts = m.get("counts", {})
            total_queued += counts.get("QUEUED", 0)
            total_processing += counts.get("PROCESSING", 0)
            total_done += counts.get("DONE", 0)
            total_failed += counts.get("FAILED", 0) + counts.get("TIMEOUT", 0)
            total_items += counts.get("TOTAL", 0)
            pool_summaries.append(m)
            
        overall_success_rate = (total_done / total_items * 100) if total_items > 0 else 100.0
        
        return {
            "total_pools": len(pools),
            "total_items": total_items,
            "total_queued": total_queued,
            "total_processing": total_processing,
            "total_done": total_done,
            "total_failed": total_failed,
            "overall_success_rate": round(overall_success_rate, 1),
            "recent_pools": pool_summaries
        }
    except Exception as e:
        logger.error(f"Erro ao gerar resumo do dashboard: {e}")
        return {
            "total_pools": 0, "total_items": 0, "total_queued": 0,
            "total_processing": 0, "total_done": 0, "total_failed": 0,
            "overall_success_rate": 0.0, "recent_pools": []
        }
