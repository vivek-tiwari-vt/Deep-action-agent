#!/usr/bin/env python3

import asyncio

from tools.event_bus import event_bus
from tools.process_sandbox import run_with_limits


def test_event_bus_publish_subscribe():
    async def run_test():
        task_id = "test_task"
        payload = {"type": "ping", "data": 1}

        async def reader():
            async for evt in event_bus.subscribe(task_id):
                assert evt == payload
                return True

        reader_task = asyncio.create_task(reader())
        await asyncio.sleep(0.01)
        await event_bus.publish(task_id, payload)
        ok = await asyncio.wait_for(reader_task, timeout=1)
        assert ok is True

    asyncio.run(run_test())


def test_run_with_limits_timeout():
    completed = run_with_limits(["python", "-c", "import time; time.sleep(1)"], timeout=0.1)
    assert completed.returncode != 0
    assert "Timed out" in completed.stderr

