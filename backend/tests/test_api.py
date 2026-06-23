from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.database.connection import Base, engine, SessionLocal
from app.models.models import Query, Business, Conflict

# Setup test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    # Make sure tables are created
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Clean up
    db.query(Conflict).delete()
    db.query(Business).delete()
    db.query(Query).delete()
    db.commit()
    yield
    # Clean up after test
    db.query(Conflict).delete()
    db.query(Business).delete()
    db.query(Query).delete()
    db.commit()
    db.close()

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "redis_connected" in data

def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_queries"] == 0
    assert data["total_businesses"] == 0

def test_trigger_research_endpoint():
    response = client.post("/api/research", json={"query": "Cardiologists in Birmingham"})
    assert response.status_code == 201
    data = response.json()
    assert data["query_text"] == "Cardiologists in Birmingham"
    assert data["status"] == "pending"
    assert "id" in data
