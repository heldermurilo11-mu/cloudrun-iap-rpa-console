from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from orchestrator.services import firestore_service as service


def test_versioned_metrics_read_only_parent_document():
    pool = MagicMock()
    pool.get.return_value.to_dict.return_value = {
        "counters_version": 1,
        "counts": {"QUEUED": 2, "PROCESSING": 1, "DONE": 20, "FAILED": 1, "TOTAL": 24},
    }
    db = MagicMock()
    db.collection.return_value.document.return_value = pool
    with patch.object(service, "get_db", return_value=db), patch.object(service, "_metrics_cache", {}):
        result = service.get_datapool_metrics("datapools_staging_test")
    assert result["counts"]["DONE"] == 20
    assert result["counts"]["TOTAL"] == 24
    pool.get.assert_called_once()
    pool.collection.return_value.stream.assert_not_called()
    pool.collection.return_value.count.assert_not_called()
    pool.update.assert_not_called()


def test_legacy_metrics_use_aggregates_not_stream():
    pool = MagicMock()
    pool.get.return_value.to_dict.return_value = {}
    items = pool.collection.return_value
    items.count.return_value.get.return_value = [[SimpleNamespace(value=10)]]
    def where(*, filter):
        query = MagicMock()
        query.count.return_value.get.return_value = [[SimpleNamespace(value=4 if filter.value == "DONE" else 0)]]
        return query
    items.where.side_effect = where
    db = MagicMock()
    db.collection.return_value.document.return_value = pool
    with patch.object(service, "get_db", return_value=db), patch.object(service, "_metrics_cache", {}):
        result = service.get_datapool_metrics("datapools_staging_test")
    assert result["counts"]["TOTAL"] == 10
    assert result["counts"]["DONE"] == 4
    assert result["counts"]["QUEUED"] == 6
    items.stream.assert_not_called()
    items.select.assert_not_called()


def test_inconsistent_counters_do_not_return_success():
    db = MagicMock()
    db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        "counters_version": 1, "counts": {"DONE": 10, "TOTAL": 1},
    }
    with patch.object(service, "get_db", return_value=db), patch.object(service, "_metrics_cache", {}):
        result = service.get_datapool_metrics("datapools_staging_test")
    assert "error" in result
