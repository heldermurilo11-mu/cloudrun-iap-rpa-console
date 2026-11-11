"""
Serviço de consulta de logs estruturados no Google Cloud Logging.
"""
import logging
from typing import List, Dict, Any, Optional
from google.cloud import logging_v2
from orchestrator.config import settings

logger = logging.getLogger("orchestrator.logging_service")

_client: Optional[logging_v2.Client] = None

def get_logging_client() -> logging_v2.Client:
    global _client
    if _client is None:
        _client = logging_v2.Client(project=settings.GCP_PROJECT_ID)
    return _client

def list_logs(
    severity: Optional[str] = None,
    job_name: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Busca logs estruturados dos robôs no Cloud Logging.
    """
    client = get_logging_client()
    
    bot_log_names = (
        [name.strip() for name in settings.BOT_LOG_NAMES.split(",") if name.strip()]
        if isinstance(settings.BOT_LOG_NAMES, str)
        else [str(name).strip() for name in settings.BOT_LOG_NAMES if str(name).strip()]
    )
    log_clauses = [
        'resource.type = "cloud_run_job"',
        f'logName : "{settings.AUDIT_LOG_NAME}"',
    ]
    for bot_log_name in bot_log_names:
        log_clauses.append(f'logName : "{bot_log_name}"')

    filter_parts = [f"({' OR '.join(log_clauses)})"]
    
    if severity and severity.upper() != "ALL":
        filter_parts.append(f'severity >= {severity.upper()}')
        
    if job_name:
        if not settings.is_job_allowed(job_name):
            raise ValueError(f"Job '{job_name}' não permitido.")
        filter_parts.append(f'resource.labels.job_name = "{job_name}"')
        
    query_filter = " AND ".join(filter_parts)
    
    results = []
    try:
        entries = client.list_entries(
            filter_=query_filter,
            order_by=logging_v2.DESCENDING,
            page_size=min(limit, 100)
        )
        
        count = 0
        for entry in entries:
            if count >= limit:
                break
                
            payload = entry.payload
            message = ""
            if isinstance(payload, dict):
                message = payload.get("message", str(payload))
            else:
                message = str(payload)
                
            results.append({
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
                "severity": entry.severity,
                "log_name": entry.log_name.split("/")[-1] if entry.log_name else "",
                "resource": entry.resource.type if entry.resource else "",
                "message": message,
                "payload": payload if isinstance(payload, dict) else {"raw": str(payload)}
            })
            count += 1
            
        return results
    except Exception as e:
        logger.error(f"Erro ao buscar logs no Cloud Logging: {e}")
        return []
