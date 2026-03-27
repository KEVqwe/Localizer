import pytest
from fastapi.testclient import TestClient
from server.src.api.router import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_job_approval_flow():
    response = client.post("/api/v1/jobs/approve/123", json={
        "validated_subtitles": [{"text": "Hello", "start": 0}],
        "validated_ui_elements": []
    })
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS_PHASE_2"
