import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db import Base, get_db
from src.main import app


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_eval.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_evaluate_and_fetch_run(client):
    payload = {
        "model_name": "qwen2.5-coder:7b",
        "prompt": "Return invoice status as JSON.",
        "response_text": '{"status": "paid"}',
        "expected_json_keys": ["status"],
        "latency_ms": 320.0,
    }
    post_res = client.post("/evaluate", json=payload)
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["overall_passed"] is True
    assert data["run_id"] == 1

    get_res = client.get("/runs/1")
    assert get_res.status_code == 200
    assert get_res.json()["model_name"] == "qwen2.5-coder:7b"

    list_res = client.get("/runs")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_evaluate_fails_on_pii_and_persists(client):
    payload = {
        "model_name": "gpt-4o-mini",
        "prompt": "Give me the customer contact.",
        "response_text": "Email them at anna@example.de",
    }
    res = client.post("/evaluate", json=payload)
    assert res.status_code == 200
    assert res.json()["overall_passed"] is False


def test_get_missing_run_returns_404(client):
    res = client.get("/runs/999")
    assert res.status_code == 404