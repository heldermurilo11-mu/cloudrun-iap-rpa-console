"""
Módulo de Configuração Centralizada e Allowlists de Recursos.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _parse_csv_list(env_var: str, default: str = "", lower: bool = False) -> List[str]:
    """Faz o parsing seguro de variáveis separadas por vírgula."""
    raw = os.getenv(env_var, default)
    items = []
    for item in raw.split(","):
        cleaned = item.strip()
        if lower:
            cleaned = cleaned.lower()
        if cleaned:
            items.append(cleaned)
    return items


class Settings:
    # Ambiente
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local").lower()
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # GCP Core
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", os.getenv("GCP_STORAGE_BUCKET", ""))

    # Allowlists Estritas de Recursos
    ALLOWED_DATAPOOL_PREFIXES: List[str] = _parse_csv_list(
        "ALLOWED_DATAPOOL_PREFIXES",
        "sample_queue_,datapools_staging",
    )

    ALLOWED_JOBS: List[str] = _parse_csv_list(
        "ALLOWED_JOBS",
        "sample-producer-job,sample-consumer-job",
    )

    ALLOWED_SCHEDULERS: List[str] = _parse_csv_list(
        "ALLOWED_SCHEDULERS",
        "cron-producer,cron-consumer",
    )

    # Autenticação & IAP
    AUTH_MODE: str = os.getenv("AUTH_MODE", "local").lower()  # "iap" ou "local"
    IAP_EXPECTED_AUDIENCE: str = os.getenv("IAP_EXPECTED_AUDIENCE", "")
    IAP_ALLOWED_DOMAINS: List[str] = _parse_csv_list("IAP_ALLOWED_DOMAINS", "", lower=True)
    IAP_ADMIN_EMAILS: List[str] = _parse_csv_list("IAP_ADMIN_EMAILS", "", lower=True)
    LOCAL_DEV_USER: str = os.getenv("LOCAL_DEV_USER", "developer@example.com")
    LOCAL_DEV_ROLE: str = os.getenv("LOCAL_DEV_ROLE", "admin")

    # Cache & Otimização de Polling
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "5"))
    PAGE_SIZE_LIMIT: int = int(os.getenv("PAGE_SIZE_LIMIT", "100"))

    # Auditoria, Logs & Telemetria
    AUDIT_LOG_NAME: str = os.getenv("AUDIT_LOG_NAME", "rpa-orchestrator-audit")
    AUDIT_FIRESTORE_COLLECTION: str = os.getenv("AUDIT_FIRESTORE_COLLECTION", "audit_trail")
    BOT_LOG_NAMES: List[str] = _parse_csv_list("BOT_LOG_NAMES", "rpa-bots-worker")
    EXECUTIONS_COLLECTION: str = os.getenv("EXECUTIONS_COLLECTION", "executions")
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "UTC")

    def is_datapool_allowed(self, collection_name: str) -> bool:
        """Valida se o datapool pertence à lista autorizada."""
        return any(collection_name.startswith(p) for p in self.ALLOWED_DATAPOOL_PREFIXES)

    def is_job_allowed(self, job_name: str) -> bool:
        """Valida se o Cloud Run Job pertence à lista autorizada."""
        return job_name in self.ALLOWED_JOBS

    def is_scheduler_allowed(self, scheduler_name: str) -> bool:
        """Valida se o Cloud Scheduler pertence à lista autorizada."""
        return scheduler_name in self.ALLOWED_SCHEDULERS


settings = Settings()
