"""
Testes de Registro e Consulta de Auditoria.
"""
from orchestrator import audit


def test_record_audit_event_structure():
    """Testa a geração e estrutura de um evento de auditoria sanitizado."""
    event_id = audit.record_audit_event(
        actor_email="tester@example.com",
        actor_sub="user-test-123",
        action="TEST_ACTION",
        target_resource="sample_queue_demo",
        result_code="SUCCESS",
        sample_ref="SAMPLE-99001",
        prev_status="FAILED",
        new_status="QUEUED",
        reason="Teste automatizado de auditoria"
    )
    assert event_id.startswith("audit_")


def test_list_audit_endpoint(client):
    """Verifica se o endpoint de auditoria responde com status 200."""
    resp = client.get("/api/audit?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert isinstance(data["events"], list)
