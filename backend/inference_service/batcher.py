from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class _Job(Generic[T, R]):
    items: list[T]
    future: asyncio.Future[list[R]]


class DynamicBatcher(Generic[T, R]):
    def __init__(
        self,
        handler: Callable[[list[T]], Awaitable[list[R]]],
        max_batch_size: int,
        max_wait_ms: int,
    ):
        self.handler = handler
        self.max_batch_size = max_batch_size
        self.max_wait_seconds = max_wait_ms / 1000
        self.queue: asyncio.Queue[_Job[T, R]] = asyncio.Queue()
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.task is None:
            self.task = asyncio.create_task(self._run())

    async def close(self) -> None:
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    async def submit(self, items: list[T]) -> list[R]:
        if not items:
            return []
        if len(items) > self.max_batch_size:
            chunks = [
                items[offset : offset + self.max_batch_size]
                for offset in range(0, len(items), self.max_batch_size)
            ]
            results = await asyncio.gather(*(self.submit(chunk) for chunk in chunks))
            return [item for result in results for item in result]
        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[R]] = loop.create_future()
        await self.queue.put(_Job(items=items, future=future))
        return await future

    async def _run(self) -> None:
        while True:
            first = await self.queue.get()
            jobs = [first]
            item_count = len(first.items)
            deadline = asyncio.get_running_loop().time() + self.max_wait_seconds
            while item_count < self.max_batch_size:
                timeout = deadline - asyncio.get_running_loop().time()
                if timeout <= 0:
                    break
                try:
                    job = await asyncio.wait_for(self.queue.get(), timeout)
                except TimeoutError:
                    break
                if item_count + len(job.items) > self.max_batch_size:
                    await self.queue.put(job)
                    break
                jobs.append(job)
                item_count += len(job.items)

            flattened = [item for job in jobs for item in job.items]
            try:
                results = await self.handler(flattened)
                offset = 0
                for job in jobs:
                    size = len(job.items)
                    job.future.set_result(results[offset : offset + size])
                    offset += size
            except Exception as exc:
                for job in jobs:
                    if not job.future.done():
                        job.future.set_exception(exc)
