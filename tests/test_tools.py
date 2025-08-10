#!/usr/bin/env python3

import pytest


def test_http_client_import():
    from tools.http_client import http_client
    assert http_client is not None


def test_vector_memory_optional():
    try:
        from tools.vector_memory import vector_memory
    except Exception:
        pytest.skip("vector memory optional dependencies not installed")
    assert vector_memory is not None

