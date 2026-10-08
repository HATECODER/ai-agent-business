from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_liveness_exposes_no_environment_or_tenant_data():
    response = TestClient(create_app()).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"service": "bizpilot-api", "status": "ok"}
    assert "server" not in {key.lower() for key in response.headers}
