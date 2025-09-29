from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_chatbot_interface():
    """Test chatbot interface endpoint"""
    response = client.get("/api/v1/chatbot")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
