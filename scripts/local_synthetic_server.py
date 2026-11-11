"""
Servidor Local de Homologação Portão A com Fixtures e Mocks 100% Sintéticos em Memória.
NENHUMA chamada externa é realizada (Zero GCP / Zero Firestore real / 100% isolado).
"""
import sys
import os
import datetime

# Injeta diretório raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.config import settings

# Garante modo estritamente local e seguro
settings.ENVIRONMENT = "local"
settings.AUTH_MODE = "local"
settings.LOCAL_DEV_USER = "staging@example.com"
settings.LOCAL_DEV_ROLE = "operator"

# Fixtures Sintéticas
SYNTHETIC_POOLS = ["datapools_staging_demo", "sample_queue_demo"]

SYNTHETIC_ITEMS = [
    {
        "id": "mock_xss_01",
        "sample_ref": "<script>window.XSS_SCRIPT_EXECUTED=true;document.title='XSS_COMPROMISED';</script>SAMPLE-XSS-SCRIPT",
        "file_name": "<img src=invalid_source onerror='window.XSS_IMG_EXECUTED=true;'>batch_xss_img.pdf",
        "status": "QUEUED",
        "attempts": 0,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "is_synthetic": True,
        "payload": {
            "identificacao": "<script>alert('payload_xss')</script>",
            "category": "<b onmouseover='window.XSS_MATRIZ=true'>Documento Sintético</b>"
        }
    }
] + [
    {
        "id": f"mock_{1000 + i}",
        "sample_ref": f"SAMPLE-99{i:03d}",
        "file_name": f"batch_demo_{i // 3 + 1:02d}.pdf",
        "status": ["QUEUED", "PROCESSING", "DONE", "DONE", "FAILED", "TIMEOUT", "CANCELED", "DONE", "QUEUED", "DONE"][i % 10],
        "attempts": (i % 3),
        "created_at": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=i*15)).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "is_synthetic": True,
        "external_ref": f"EXT-8877{i:02d}" if i % 2 == 0 else None,
        "error_msg": "Falha na leitura do QR code do documento" if (i % 5 == 4) else None,
        "payload": {
            "identificacao": f"SAMPLE-99{i:03d}",
            "category": "Documento Sintético",
            "source_node": f"Origem de Coleta #{i + 1}"
        }
    }
    for i in range(1, 35)  # 34 itens para validar paginação
]

SYNTHETIC_JOBS = [
    {
        "job_name": "sample-producer-job",
        "full_name": f"projects/{settings.GCP_PROJECT_ID or 'your-gcp-project-id'}/locations/{settings.GCP_REGION}/jobs/sample-producer-job",
        "image": f"{settings.GCP_REGION}-docker.pkg.dev/{settings.GCP_PROJECT_ID or 'your-gcp-project-id'}/rpa-images/sample-producer-job:latest",
        "cpu": "1",
        "memory": "1Gi",
        "timeout": "900s",
        "status": "READY"
    },
    {
        "job_name": "sample-consumer-job",
        "full_name": f"projects/{settings.GCP_PROJECT_ID or 'your-gcp-project-id'}/locations/{settings.GCP_REGION}/jobs/sample-consumer-job",
        "image": f"{settings.GCP_REGION}-docker.pkg.dev/{settings.GCP_PROJECT_ID or 'your-gcp-project-id'}/rpa-images/sample-consumer-job:latest",
        "cpu": "1",
        "memory": "2Gi",
        "timeout": "1800s",
        "status": "READY"
    }
]

SYNTHETIC_EXECUTIONS = [
    {
        "execution_id": "sample-producer-job-demo-01",
        "bot_name": "sample-producer-job",
        "status": "SUCCESS",
        "processed_items": 15,
        "total_items": 15,
        "started_at": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).isoformat(),
        "message": "Execução sintética finalizada com 100% de sucesso"
    },
    {
        "execution_id": "sample-consumer-job-demo-02",
        "bot_name": "sample-consumer-job",
        "status": "SUCCESS",
        "processed_items": 14,
        "total_items": 15,
        "started_at": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat(),
        "message": "Execução sintética finalizada (1 item com retry pendente)"
    }
]

SYNTHETIC_SCHEDULERS = [
    {
        "scheduler_name": "cron-producer",
        "full_name": f"projects/{settings.GCP_PROJECT_ID or 'your-gcp-project-id'}/locations/{settings.GCP_REGION}/jobs/cron-producer",
        "schedule": "*/15 * * * *",
        "timezone": settings.DEFAULT_TIMEZONE,
        "state": "PAUSED",
        "description": "Gatilho automático de coleta (Pausado para Staging)",
        "status": "READY"
    },
    {
        "scheduler_name": "cron-consumer",
        "full_name": f"projects/{settings.GCP_PROJECT_ID or 'your-gcp-project-id'}/locations/{settings.GCP_REGION}/jobs/cron-consumer",
        "schedule": "*/40 * * * *",
        "timezone": settings.DEFAULT_TIMEZONE,
        "state": "PAUSED",
        "description": "Gatilho automático de consumo (Pausado para Staging)",
        "status": "READY"
    }
]

SYNTHETIC_LOGS = [
    {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "severity": "INFO",
        "log_name": "sample-producer-job",
        "message": "Inicialização do worker OCR em modo sintético isolado."
    },
    {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "severity": "WARNING",
        "log_name": "sample-consumer-job",
        "message": "Item SAMPLE-99005 necessitou de 2 tentativas de parsing."
    },
    {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "severity": "INFO",
        "log_name": "sample-consumer-job",
        "message": "Fila processada com sucesso. Itens gravados no staging."
    }
]

SYNTHETIC_AUDIT = [
    {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "actor_email": "staging@example.com",
        "action": "CONSOLE_ACCESS",
        "target_resource": "dashboard_overview",
        "result_code": "SUCCESS",
        "reason": "Acesso de auditoria read-only autorizado no Portão A."
    },
    {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "actor_email": "staging@example.com",
        "action": "QUERY_DATAPOOL",
        "target_resource": "sample_queue_demo",
        "result_code": "SUCCESS",
        "reason": "Inspeção visual da fila de demonstração."
    }
]


# Funções Mock
def mock_list_datapools():
    return SYNTHETIC_POOLS


def mock_get_metrics(name):
    if not settings.is_datapool_allowed(name):
        raise ValueError(f"Datapool '{name}' fora da allowlist.")
    items = SYNTHETIC_ITEMS
    counts = {"QUEUED": 0, "PROCESSING": 0, "DONE": 0, "FAILED": 0, "TIMEOUT": 0, "CANCELED": 0, "TOTAL": len(items)}
    for it in items:
        st = it.get("status", "QUEUED")
        counts[st] = counts.get(st, 0) + 1
    return {
        "datapool": name,
        "counts": counts,
        "success_rate": round(counts["DONE"] / counts["TOTAL"] * 100, 1) if counts["TOTAL"] > 0 else 0,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def mock_list_items(datapool_name, status_filter=None, search_query=None, limit=50, start_after_id=None):
    if not settings.is_datapool_allowed(datapool_name):
        raise ValueError(f"Datapool '{datapool_name}' fora da allowlist.")
    filtered = SYNTHETIC_ITEMS
    if status_filter and status_filter != "ALL":
        filtered = [i for i in filtered if i.get("status") == status_filter]
    if search_query:
        q = search_query.lower()
        filtered = [i for i in filtered if q in i.get("sample_ref", "").lower() or q in i.get("file_name", "").lower() or q in i.get("id", "").lower()]

    start_idx = 0
    if start_after_id:
        for idx, item in enumerate(filtered):
            if item["id"] == start_after_id:
                start_idx = idx + 1
                break
    page = filtered[start_idx:start_idx + limit]
    next_cursor = page[-1]["id"] if len(page) == limit and (start_idx + limit) < len(filtered) else None
    return {
        "datapool": datapool_name,
        "items": page,
        "count": len(page),
        "total_filtered": len(filtered),
        "next_cursor": next_cursor
    }


def mock_get_item_details(datapool_name, item_id):
    for i in SYNTHETIC_ITEMS:
        if i["id"] == item_id:
            return i
    return None


def mock_get_dashboard_summary():
    m1 = mock_get_metrics("datapools_staging_demo")
    m2 = mock_get_metrics("sample_queue_demo")
    return {
        "total_pools": len(SYNTHETIC_POOLS),
        "total_items": m1["counts"]["TOTAL"] + m2["counts"]["TOTAL"],
        "total_queued": m1["counts"]["QUEUED"] + m2["counts"]["QUEUED"],
        "total_processing": m1["counts"]["PROCESSING"] + m2["counts"]["PROCESSING"],
        "total_done": m1["counts"]["DONE"] + m2["counts"]["DONE"],
        "total_failed": m1["counts"]["FAILED"] + m1["counts"]["TIMEOUT"] + m2["counts"]["FAILED"],
        "overall_success_rate": 78.5,
        "recent_pools": [m1, m2]
    }


# Aplicar Mocks nos serviços
from orchestrator.services import firestore_service, cloudrun_service, scheduler_service, logging_service
from orchestrator import audit

firestore_service.list_datapool_collections = mock_list_datapools
firestore_service.get_datapool_metrics = mock_get_metrics
firestore_service.list_datapool_items = mock_list_items
firestore_service.get_item_details = mock_get_item_details
firestore_service.get_dashboard_summary = mock_get_dashboard_summary

cloudrun_service.list_allowed_jobs = lambda: SYNTHETIC_JOBS
cloudrun_service.list_job_executions = lambda job_name=None, limit=30: SYNTHETIC_EXECUTIONS
scheduler_service.list_allowed_schedulers = lambda: SYNTHETIC_SCHEDULERS
logging_service.list_logs = lambda severity=None, job_name=None, limit=50: SYNTHETIC_LOGS
audit.list_audit_events = lambda limit=50, start_after=None: SYNTHETIC_AUDIT

if __name__ == "__main__":
    import uvicorn
    from orchestrator.server import app
    print("=== INICIANDO SERVIDOR LOCAL SINTÉTICO PORTÃO A ===")
    print("Modo: 100% Sintético / Localhost Isolado")
    print("URL: http://127.0.0.1:8080")
    print("Pressione Ctrl+C para encerrar.")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")
