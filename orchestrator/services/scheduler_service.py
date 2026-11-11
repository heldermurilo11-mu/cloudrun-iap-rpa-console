"""
Serviço de consulta de Agendamentos no Google Cloud Scheduler.
"""
import logging
from typing import List, Dict, Any, Optional
from orchestrator.config import settings

logger = logging.getLogger("orchestrator.scheduler")

try:
    from google.cloud import scheduler_v1
except ImportError:
    scheduler_v1 = None

_client: Optional[Any] = None

def get_scheduler_client():
    global _client
    if _client is None and scheduler_v1 is not None:
        try:
            _client = scheduler_v1.CloudSchedulerClient()
        except Exception as e:
            logger.warning(f"Falha ao instanciar CloudSchedulerClient: {e}")
    return _client

def list_allowed_schedulers() -> List[Dict[str, Any]]:
    """
    Lista agendamentos homologados com seus estados e expressões cron.
    """
    results = []
    client = get_scheduler_client()
    parent = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_REGION}"
    
    for sched_name in settings.ALLOWED_SCHEDULERS:
        sched_full_name = f"{parent}/jobs/{sched_name}"
        if client is None:
            results.append({
                "scheduler_name": sched_name,
                "full_name": sched_full_name,
                "schedule": "*/15 * * * *" if "producer" in sched_name else "*/40 * * * *",
                "timezone": settings.DEFAULT_TIMEZONE,
                "state": "PAUSED",
                "description": "Trigger automático",
                "status": "READY"
            })
            continue
        try:
            job = client.get_job(name=sched_full_name)
            
            state_str = "UNKNOWN"
            if job.state == scheduler_v1.Job.State.ENABLED:
                state_str = "ENABLED"
            elif job.state == scheduler_v1.Job.State.PAUSED:
                state_str = "PAUSED"
            elif job.state == scheduler_v1.Job.State.DISABLED:
                state_str = "DISABLED"
                
            results.append({
                "scheduler_name": sched_name,
                "full_name": job.name,
                "schedule": job.schedule,
                "timezone": job.time_zone or settings.DEFAULT_TIMEZONE,
                "state": state_str,
                "description": job.description or "",
                "status": "READY"
            })
        except Exception as e:
            logger.warning(f"Não foi possível obter agendamento '{sched_name}': {e}")
            results.append({
                "scheduler_name": sched_name,
                "full_name": sched_full_name,
                "schedule": "N/A",
                "timezone": settings.DEFAULT_TIMEZONE,
                "state": "UNAVAILABLE",
                "error": str(e)
            })
            
    return results
