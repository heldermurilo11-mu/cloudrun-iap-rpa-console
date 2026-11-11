"""
Script de Benchmark de Latência p50/p95 para Homologação Local do Portão A.
Amostra mínima de 35 chamadas por endpoint.
"""
import time
import requests
import statistics

BASE_URL = "http://127.0.0.1:8080"
SAMPLES = 35

endpoints = [
    ("/healthz", "Health Check"),
    ("/", "SPA Index HTML"),
    ("/api/datapools", "Listar Datapools"),
    ("/api/datapools/summary", "Resumo de KPIs do Dashboard"),
    ("/api/datapools/sample_queue_demo/metrics", "Métricas da Fila"),
    ("/api/datapools/sample_queue_demo/items?limit=10", "Listar Itens (Página 1, 10 itens)"),
    ("/api/datapools/sample_queue_demo/items?limit=10&cursor=mock_1010", "Paginação (Cursor Página 2)"),
    ("/api/datapools/sample_queue_demo/items/mock_1001", "Detalhes de Item JSON"),
    ("/api/jobs", "Catálogo de Jobs"),
    ("/api/jobs/executions?limit=30", "Histórico de Execuções"),
    ("/api/schedulers", "Lista de Agendamentos"),
    ("/api/logs?limit=50", "Logs Estruturados"),
    ("/api/audit?limit=50", "Trilha de Auditoria")
]

print("=== BENCHMARK DE LATÊNCIA (p50 / p95) — AMBIENTE LOCALHOST ===")
print(f"Número de amostras por endpoint: {SAMPLES}\n")
print("| Endpoint | Descrição | Status HTTP | Qtd Itens / Resposta | Latência p50 (ms) | Latência p95 (ms) |")
print("|---|---|---|---|---|---|")

for path, desc in endpoints:
    url = f"{BASE_URL}{path}"
    durations = []
    status = 0
    resp_info = ""
    
    for i in range(SAMPLES):
        start = time.perf_counter()
        r = requests.get(url)
        dur = (time.perf_counter() - start) * 1000 # ms
        durations.append(dur)
        status = r.status_code
        if i == 0:
            if r.headers.get("content-type", "").startswith("application/json"):
                data = r.json()
                if isinstance(data, dict):
                    if "items" in data:
                        resp_info = f"{len(data['items'])} itens (next: {data.get('next_cursor')})"
                    elif "datapools" in data:
                        resp_info = f"{len(data['datapools'])} pools"
                    elif "jobs" in data:
                        resp_info = f"{len(data['jobs'])} jobs"
                    elif "schedulers" in data:
                        resp_info = f"{len(data['schedulers'])} schedulers"
                    elif "logs" in data:
                        resp_info = f"{len(data['logs'])} logs"
                    elif "events" in data:
                        resp_info = f"{len(data['events'])} audit logs"
                    elif "counts" in data:
                        resp_info = f"total {data['counts'].get('TOTAL', 0)} itens"
                    elif "total_items" in data:
                        resp_info = f"{data['total_pools']} pools / {data['total_items']} itens"
                    else:
                        resp_info = f"JSON {len(data)} chaves"
                else:
                    resp_info = f"JSON {len(data)} itens"
            else:
                resp_info = f"HTML ({len(r.text)} bytes)"

    durations.sort()
    # p50 (mediana)
    p50 = statistics.median(durations)
    # p95 (95th percentile)
    idx_p95 = int(round(0.95 * len(durations))) - 1
    p95 = durations[max(0, min(idx_p95, len(durations) - 1))]
    
    print(f"| `{path}` | {desc} | {status} OK | {resp_info} | {p50:.2f} ms | {p95:.2f} ms |")

print("\nNota: Latências medidas em ambiente localhost sintético; não representam latências de rede do Cloud Run produtivo.")
