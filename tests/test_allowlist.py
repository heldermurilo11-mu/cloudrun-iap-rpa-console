"""
Testes de Allowlists de Recursos (Datapools, Jobs e Schedulers).
"""
from orchestrator.config import settings


def test_allowed_datapool_prefixes(monkeypatch):
    """Valida a lógica de filtragem de prefixos de Datapools."""
    monkeypatch.setattr(settings, "ALLOWED_DATAPOOL_PREFIXES", ["sample_queue_", "datapools_staging"])
    assert settings.is_datapool_allowed("sample_queue_demo") is True
    assert settings.is_datapool_allowed("datapools_staging_demo") is True
    assert settings.is_datapool_allowed("private_finance_table") is False
    assert settings.is_datapool_allowed("system_users") is False


def test_allowed_jobs(monkeypatch):
    """Valida a lógica de restrição de Cloud Run Jobs."""
    monkeypatch.setattr(settings, "ALLOWED_JOBS", ["sample-producer-job", "sample-consumer-job"])
    assert settings.is_job_allowed("sample-producer-job") is True
    assert settings.is_job_allowed("sample-consumer-job") is True
    assert settings.is_job_allowed("unauthorized-delete-job") is False


def test_allowed_schedulers(monkeypatch):
    """Valida a lógica de restrição de Cloud Schedulers."""
    monkeypatch.setattr(settings, "ALLOWED_SCHEDULERS", ["cron-producer", "cron-consumer"])
    assert settings.is_scheduler_allowed("cron-producer") is True
    assert settings.is_scheduler_allowed("cron-consumer") is True
    assert settings.is_scheduler_allowed("cron-unauthorized") is False


def test_blocked_datapool_returns_403(client, monkeypatch):
    """Verifica se consulta a datapool não autorizado retorna 403 Forbidden."""
    monkeypatch.setattr(settings, "ALLOWED_DATAPOOL_PREFIXES", ["sample_queue_", "datapools_staging"])
    resp = client.get("/api/datapools/private_finance_table/metrics")
    assert resp.status_code == 403
    assert "fora da allowlist" in resp.json()["detail"]


def test_blocked_job_returns_403(client, monkeypatch):
    """Verifica se consulta a job não autorizado retorna 403 Forbidden."""
    monkeypatch.setattr(settings, "ALLOWED_JOBS", ["sample-producer-job", "sample-consumer-job"])
    resp = client.get("/api/jobs/executions?job_name=unknown-job")
    assert resp.status_code == 403
    assert "fora da allowlist" in resp.json()["detail"]
