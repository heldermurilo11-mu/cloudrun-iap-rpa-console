"""
Módulo de Auditoria: Cloud Logging Estruturado + Firestore Read-Model.
"""
import uuid
import datetime
import logging
from typing import Dict, Any, Optional, List
from google.cloud import firestore, logging as gcp_logging
from orchestrator.config import settings

logger = logging.getLogger("orchestrator.audit")

# Clientes GCP
_db: Optional[firestore.Client] = None
_gcp_logger: Optional[Any] = None

def get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(
            project=settings.GCP_PROJECT_ID,
            database=settings.FIRESTORE_DATABASE
        )
    return _db

def get_gcp_audit_logger():
    global _gcp_logger
    if _gcp_logger is None:
        try:
            client = gcp_logging.Client(project=settings.GCP_PROJECT_ID)
            _gcp_logger = client.logger(settings.AUDIT_LOG_NAME)
        except Exception as e:
            logger.warning(f"Cloud Logging não inicializado para auditoria: {e}")
            _gcp_logger = None
    return _gcp_logger

def record_audit_event(
    actor_email: str,
    actor_sub: str,
    action: str,
    target_resource: str,
    result_code: str = "SUCCESS",
    sample_ref: Optional[str] = None,
    prev_status: Optional[str] = None,
    new_status: Optional[str] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Grava um evento de auditoria no Cloud Logging (autoritativo) e no Firestore (read-model).
    """
    event_id = f"audit_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    event_data = {
        "event_id": event_id,
        "timestamp": now_iso,
        "actor_email": actor_email,
        "actor_sub": actor_sub,
        "action": action,
        "target_resource": target_resource,
        "result_code": result_code,
        "sample_ref": sample_ref,
        "prev_status": prev_status,
        "new_status": new_status,
        "reason": reason,
        "ip_address": ip_address,
        "metadata": extra_metadata or {}
    }
    
    # 1. Registro primário autoritativo no Cloud Logging
    try:
        gcp_log = get_gcp_audit_logger()
        if gcp_log:
            gcp_log.log_struct(
                event_data,
                severity="NOTICE" if result_code == "SUCCESS" else "WARNING"
            )
    except Exception as e:
        logger.error(f"Falha ao registrar auditoria no Cloud Logging: {e}")
        
    # 2. Registro no Firestore read-model (audit_trail)
    try:
        db = get_db()
        db.collection(settings.AUDIT_FIRESTORE_COLLECTION).document(event_id).set(event_data)
    except Exception as e:
        logger.error(f"Falha ao gravar evento de auditoria no Firestore: {e}")
        
    return event_id

def list_audit_events(limit: int = 50, start_after: Optional[str] = None) -> List[Dict[str, Any]]:
    """Consulta eventos de auditoria ordenados por timestamp decrescente."""
    try:
        db = get_db()
        query = db.collection(settings.AUDIT_FIRESTORE_COLLECTION).order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(min(limit, 100))
        
        if start_after:
            last_doc = db.collection(settings.AUDIT_FIRESTORE_COLLECTION).document(start_after).get()
            if last_doc.exists:
                query = query.start_after(last_doc)
                
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Erro ao listar eventos de auditoria: {e}")
        return []
