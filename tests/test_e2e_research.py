#!/usr/bin/env python3

import os
import pytest


@pytest.mark.skipif("CI" in os.environ, reason="Skip live E2E in CI until dependencies are fully available")
def test_e2e_research_smoke():
    from main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    r = client.post("/execute", json={
        "task_description": "List three recent AI topics and summarize",
        "task_type": "research",
        "priority": "low",
        "timeout_minutes": 1
    })
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    s = client.get(f"/status/{task_id}")
    assert s.status_code == 200

