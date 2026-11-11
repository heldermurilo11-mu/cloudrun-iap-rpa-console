"""
Testes de Endpoints de Datapool e Resumo de Dashboard.
"""
def test_get_dashboard_summary(client):
    """Verifica se o endpoint de resumo do dashboard responde com os campos estruturados."""
    resp = client.get("/api/datapools/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_pools" in data
    assert "total_items" in data
    assert "overall_success_rate" in data

def test_list_datapools(client):
    """Verifica a listagem de datapools homologados."""
    resp = client.get("/api/datapools")
    assert resp.status_code == 200
    data = resp.json()
    assert "datapools" in data
    assert isinstance(data["datapools"], list)
