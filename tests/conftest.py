from __future__ import annotations

import os

import pytest
import httpx

os.environ.setdefault("OP06_ALLOW_DEMO_MODEL", "1")

from op06.api.app import app, get_pipeline
from op06.pipeline import TriagePipeline


@pytest.fixture(scope="session")
def pipeline() -> TriagePipeline:
    return TriagePipeline.build()


@pytest.fixture()
async def client():
    get_pipeline.cache_clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    get_pipeline.cache_clear()


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"
