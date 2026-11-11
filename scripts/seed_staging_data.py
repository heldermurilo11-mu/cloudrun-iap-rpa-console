"""
Script para semear dados sintéticos no ambiente de staging (sample_queue_demo).
Não afeta dados ou registros reais de produção.
"""
import os
import sys
import datetime
from google.cloud import firestore

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from orchestrator.config import settings


def seed_staging():
    print(f"[SEED] Conectando ao Firestore: {settings.FIRESTORE_DATABASE} (Projeto: {settings.GCP_PROJECT_ID})")
    db = firestore.Client(project=settings.GCP_PROJECT_ID, database=settings.FIRESTORE_DATABASE)

    pool_name = "sample_queue_demo"
    items_ref = db.collection("datapools").document(pool_name).collection("items")

    # Registra o datapool na lista de pools ativos
    db.collection("datapools").document("active_pools").set({
        "list": firestore.ArrayUnion([pool_name]),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }, merge=True)

    sample_mocks = [
        {"id": "mock_1001", "sample_ref": "SAMPLE-99001", "file_name": "batch_demo_01.pdf", "status": "QUEUED", "attempts": 0},
        {"id": "mock_1002", "sample_ref": "SAMPLE-99002", "file_name": "batch_demo_01.pdf", "status": "QUEUED", "attempts": 0},
        {"id": "mock_1003", "sample_ref": "SAMPLE-99003", "file_name": "batch_demo_01.pdf", "status": "PROCESSING", "attempts": 1, "locked_by": "worker-sim-01"},
        {"id": "mock_1004", "sample_ref": "SAMPLE-99004", "file_name": "batch_demo_02.pdf", "status": "DONE", "attempts": 1, "external_ref": "EXT-887711"},
        {"id": "mock_1005", "sample_ref": "SAMPLE-99005", "file_name": "batch_demo_02.pdf", "status": "DONE", "attempts": 1, "external_ref": "EXT-887712"},
        {"id": "mock_1006", "sample_ref": "SAMPLE-99006", "file_name": "batch_demo_02.pdf", "status": "DONE", "attempts": 1, "external_ref": "EXT-887713"},
        {"id": "mock_1007", "sample_ref": "SAMPLE-99007", "file_name": "batch_demo_03.pdf", "status": "FAILED", "attempts": 3, "error_msg": "Documento com código ilegível"},
        {"id": "mock_1008", "sample_ref": "SAMPLE-99008", "file_name": "batch_demo_03.pdf", "status": "TIMEOUT", "attempts": 3, "error_msg": "Lease expirado sem resposta do portal"},
        {"id": "mock_1009", "sample_ref": "SAMPLE-99009", "file_name": "batch_demo_04.pdf", "status": "CANCELED", "attempts": 0, "cancel_reason": "Item cancelado a pedido do solicitante"},
        {"id": "mock_1010", "sample_ref": "SAMPLE-99010", "file_name": "batch_demo_04.pdf", "status": "QUEUED", "attempts": 0}
    ]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for s in sample_mocks:
        doc_data = {
            "sample_ref": s["sample_ref"],
            "file_name": s["file_name"],
            "status": s["status"],
            "attempts": s["attempts"],
            "created_at": now,
            "updated_at": now,
            "is_synthetic": True,
            "payload": {
                "identificacao": s["sample_ref"],
                "category": "Documento Sintético",
                "source_node": "Origem de Teste 01"
            }
        }
        if "external_ref" in s:
            doc_data["external_ref"] = s["external_ref"]
        if "error_msg" in s:
            doc_data["error_msg"] = s["error_msg"]

        items_ref.document(s["id"]).set(doc_data)
        print(f"  -> Semeado: {s['sample_ref']} ({s['status']})")

    print(f"\n[OK] 10 itens sintéticos semeados com sucesso em '{pool_name}'!")


if __name__ == "__main__":
    seed_staging()
