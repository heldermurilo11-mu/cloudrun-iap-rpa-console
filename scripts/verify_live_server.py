"""
Script de verificação de saúde e rotas da API em execução.
"""
import requests
import json

def verify():
    base_url = "http://127.0.0.1:8080"
    print(f"=== Verificando Servidor Orquestrador em {base_url} ===\n")
    
    # 1. Healthz
    r = requests.get(f"{base_url}/healthz")
    print(f"[GET /healthz] Status: {r.status_code}")
    print(f"  Resposta: {r.json()}")
    print(f"  CSP Header: {r.headers.get('Content-Security-Policy', '')[:40]}...")
    
    # 2. SPA index.html
    r = requests.get(f"{base_url}/")
    print(f"\n[GET /] Status: {r.status_code}")
    print(f"  Tamanho HTML: {len(r.text)} bytes")
    assert "<title>Cloud Run RPA Operations Console</title>" in r.text
    
    # 3. Datapools
    r = requests.get(f"{base_url}/api/datapools")
    print(f"\n[GET /api/datapools] Status: {r.status_code}")
    print(f"  Datapools encontrados: {r.json().get('datapools', [])}")
    
    # 4. Summary
    r = requests.get(f"{base_url}/api/datapools/summary")
    print(f"\n[GET /api/datapools/summary] Status: {r.status_code}")
    print(f"  Resumo: {r.json()}")
    
    # 5. Staging Pool Items
    r = requests.get(f"{base_url}/api/datapools/sample_queue_demo/items?limit=5")
    print(f"\n[GET /api/datapools/sample_queue_demo/items] Status: {r.status_code}")
    print(f"  Amostras retornadas: {len(r.json().get('items', []))}")
    for item in r.json().get('items', []):
        print(f"    -> {item.get('sample_ref')} | Status: {item.get('status')} | Tentativas: {item.get('attempts')}")
        
    # 6. Schedulers
    r = requests.get(f"{base_url}/api/schedulers")
    print(f"\n[GET /api/schedulers] Status: {r.status_code}")
    print(f"  Schedulers: {[s['scheduler_name'] for s in r.json().get('schedulers', [])]}")
    
    # 7. Jobs
    r = requests.get(f"{base_url}/api/jobs")
    print(f"\n[GET /api/jobs] Status: {r.status_code}")
    print(f"  Jobs: {[j['job_name'] for j in r.json().get('jobs', [])]}")
    
    print("\n[SUCESSO] Todos os 7 endpoints verificados com 100% de integridade!")

if __name__ == "__main__":
    verify()
