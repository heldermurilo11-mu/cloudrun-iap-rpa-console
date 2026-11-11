"""
Serviço de consulta de Cloud Run Jobs e histórico de Execuções.
"""
import logging
from typing import List, Dict, Any, Optional
from orchestrator.config import settings

logger = logging.getLogger("orchestrator.cloudrun")

try:
    from google.cloud import run_v2
except ImportError:
    run_v2 = None

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

_jobs_client: Optional[Any] = None
_exec_client: Optional[Any] = None

def get_jobs_client():
    global _jobs_client
    if _jobs_client is None and run_v2 is not None:
        try:
            _jobs_client = run_v2.JobsClient()
        except Exception as e:
            logger.warning(f"Falha ao instanciar JobsClient: {e}")
    return _jobs_client

def get_exec_client():
    global _exec_client
    if _exec_client is None and run_v2 is not None:
        try:
            _exec_client = run_v2.ExecutionsClient()
        except Exception as e:
            logger.warning(f"Falha ao instanciar ExecutionsClient: {e}")
    return _exec_client

def list_allowed_jobs() -> List[Dict[str, Any]]:
    """
    Lista apenas os Cloud Run Jobs permitidos pela allowlist e seus metadados.
    """
    results = []
    client = get_jobs_client()
    parent = f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_REGION}"
    
    for job_name in settings.ALLOWED_JOBS:
        job_full_name = f"{parent}/jobs/{job_name}"
        if client is None:
            results.append({
                "job_name": job_name,
                "full_name": job_full_name,
                "image": f"{settings.GCP_REGION}-docker.pkg.dev/{settings.GCP_PROJECT_ID or 'your-project'}/rpa-images/{job_name}:latest",
                "cpu": "1",
                "memory": "1Gi" if "producer" in job_name else "2Gi",
                "timeout": "900s" if "producer" in job_name else "1800s",
                "status": "READY"
            })
            continue
        try:
            job = client.get_job(name=job_full_name)
            container = job.template.template.containers[0] if job.template.template.containers else None
            
            results.append({
                "job_name": job_name,
                "full_name": job.name,
                "image": container.image if container else "N/A",
                "cpu": container.resources.limits.get("cpu", "1") if container and container.resources else "1",
                "memory": container.resources.limits.get("memory", "1Gi") if container and container.resources else "1Gi",
                "timeout": str(job.template.template.timeout) if job.template.template.timeout else "600s",
                "max_retries": job.template.template.max_retries,
                "status": "READY"
            })
        except Exception as e:
            logger.warning(f"Não foi possível obter detalhes do job '{job_name}': {e}")
            results.append({
                "job_name": job_name,
                "full_name": job_full_name,
                "image": "N/A",
                "status": "UNAVAILABLE",
                "error": str(e)
            })
            
    return results

def list_job_executions(job_name: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Lista histórico de execuções correlacionando dados do Cloud Run e Firestore.
    """
    if job_name and not settings.is_job_allowed(job_name):
        raise ValueError(f"Job '{job_name}' não permitido.")
        
    executions = []
    
    # 1. Busca execuções na coleção configurada do Firestore (registradas pelos robôs)
    try:
        from orchestrator.services.firestore_service import get_db
        db = get_db()
        query = db.collection(settings.EXECUTIONS_COLLECTION).order_by("started_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        if job_name:
            query = query.where("bot_name", "==", job_name)
            
        docs = query.stream()
        for doc in docs:
            d = doc.to_dict()
            d["execution_id"] = doc.id
            d["source"] = "bot_telemetry"
            executions.append(d)
    except Exception as e:
        logger.warning(f"Falha ao consultar histórico de execuções no Firestore: {e}")
        
    return executions
