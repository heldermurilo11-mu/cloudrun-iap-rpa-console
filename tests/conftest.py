"""
Configurações e Fixtures para PyTest.
"""
import pytest
from fastapi.testclient import TestClient
from orchestrator.server import app
from orchestrator.config import settings

@pytest.fixture
def client():
    settings.ENVIRONMENT = "test"
    settings.AUTH_MODE = "local"
    return TestClient(app)
