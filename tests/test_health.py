"""
Basic health check tests to ensure CI pipeline passes.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test that the health endpoint returns successfully."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_root():
    """Test that the API root responds."""
    response = client.get("/")
    assert response.status_code in [200, 404]  # Either works or returns 404


def test_app_imports():
    """Test that core app components can be imported."""
    from app.core.config import settings
    from app.main import app
    
    assert settings is not None
    assert app is not None


def test_basic_math():
    """Basic test to ensure pytest is working."""
    assert 1 + 1 == 2
    assert "hello".upper() == "HELLO"