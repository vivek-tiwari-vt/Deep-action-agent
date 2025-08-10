#!/usr/bin/env python3
"""
Simple in-process async event bus for streaming task events (tokens, tools, progress).
"""

import asyncio
from typing import Dict, Any, AsyncGenerator


class EventBus:
    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue] = {}

    def _get_queue(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue()
        return self._queues[task_id]

    async def publish(self, task_id: str, event: Dict[str, Any]) -> None:
        await self._get_queue(task_id).put(event)

    async def subscribe(self, task_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        queue = self._get_queue(task_id)
        while True:
            event = await queue.get()
            yield event


event_bus = EventBus()

