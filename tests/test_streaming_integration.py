#!/usr/bin/env python3

from fastapi.testclient import TestClient
from main import app


def test_health_endpoint():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200

