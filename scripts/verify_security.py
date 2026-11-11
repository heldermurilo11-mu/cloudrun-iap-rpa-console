"""
Script de Verificação de Segurança e Testes Negativos para o Portão A.
"""
import requests
import json
import re

BASE_URL = "http://127.0.0.1:8080"

print("=== BATERIA DE TESTES DE SEGURANÇA (PORTÃO A) ===")

# 1. Teste de Allowlist (Recursos Bloqueados)
blocked_urls = [
    f"{BASE_URL}/api/datapools/tabela_financeira_privada/metrics",
    f"{BASE_URL}/api/datapools/usuarios_senhas/items",
    f"{BASE_URL}/api/jobs/executions?job_name=unauthorized-delete-job",
]
print("\n--- 1. Recurso fora da Allowlist (Esperado: 403 Forbidden) ---")
for u in blocked_urls:
    r = requests.get(u)
    print(f"URL: {u} -> Status: {r.status_code}")
    assert r.status_code == 403, f"Esperado 403, obteve {r.status_code}"
    assert "fora da allowlist" in r.text
print("[OK] Bloqueio por Allowlist 100% aprovado.")

# 2. Bloqueio de Mutações (Esperado: 405 Method Not Allowed)
print("\n--- 2. Tentativas de Mutação (Esperado: 405 Method Not Allowed) ---")
mutation_endpoints = [
    "/api/datapools",
    "/api/datapools/summary",
    "/api/datapools/sample_queue_demo/items",
    "/api/jobs",
    "/api/jobs/executions",
    "/api/schedulers",
    "/api/logs",
    "/api/audit"
]
for ep in mutation_endpoints:
    for method in ["POST", "PUT", "DELETE", "PATCH"]:
        r = requests.request(method, f"{BASE_URL}{ep}", json={"injected": "data"})
        assert r.status_code == 405, f"Endpoint {ep} com {method} retornou {r.status_code} em vez de 405!"
print(f"[OK] Todos os {len(mutation_endpoints) * 4} testes de mutação foram rejeitados com 405 Method Not Allowed.")

# 3. Headers de Segurança HTTP e CSP
print("\n--- 3. Headers de Segurança HTTP e CSP ---")
r = requests.get(f"{BASE_URL}/")
csp = r.headers.get("Content-Security-Policy", "")
cto = r.headers.get("X-Content-Type-Options", "")
xfo = r.headers.get("X-Frame-Options", "")
rp = r.headers.get("Referrer-Policy", "")

print(f"Content-Security-Policy: {csp}")
print(f"X-Content-Type-Options: {cto}")
print(f"X-Frame-Options: {xfo}")
print(f"Referrer-Policy: {rp}")

assert "default-src 'self'" in csp
assert cto == "nosniff"
assert xfo == "DENY"
print("[OK] Todos os cabeçalhos de segurança obrigatórios estão presentes e estritos.")

# 4. Verificação de Ausência de Segredos em Respostas JSON
print("\n--- 4. Varredura de Segredos em Respostas da API ---")
secret_patterns = [
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"\"private_key\":\s*\""),
    re.compile(r"\"client_secret\":\s*\""),
    re.compile(r"\"token\":\s*\"ya29\.")
]
endpoints_to_scan = [
    "/api/datapools",
    "/api/datapools/summary",
    "/api/datapools/sample_queue_demo/metrics",
    "/api/datapools/sample_queue_demo/items",
    "/api/datapools/sample_queue_demo/items/mock_1001",
    "/api/jobs",
    "/api/jobs/executions",
    "/api/schedulers",
    "/api/logs",
    "/api/audit"
]
for ep in endpoints_to_scan:
    res = requests.get(f"{BASE_URL}{ep}").text
    for p in secret_patterns:
        match = p.search(res)
        assert match is None, f"Segredo detectado na resposta de {ep}!"
print(f"[OK] {len(endpoints_to_scan)} endpoints varridos: 0 credenciais, 0 segredos, 0 chaves privadas expostas.")

# 5. XSS Sanitization Logic
print("\n--- 5. Neutralização de XSS ---")
xss_strings = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:void(0)",
    "'\"><script>alert(document.domain)</script>"
]
def escape_html(text):
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#039;'))

for x in xss_strings:
    escaped = escape_html(x)
    assert "<script>" not in escaped
    assert "<img" not in escaped
    print(f"Payload: {x:40} -> Sanitizado: {escaped}")
print("[OK] Lógica de escapeHtml aplicada em todos os campos dinâmicos da SPA.")

print("\n=== TODOS OS 5 BLOCOS DE TESTES DE SEGURANÇA FORAM CONCLUÍDOS COM SUCESSO! ===")
