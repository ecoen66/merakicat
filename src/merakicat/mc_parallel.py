# -*- coding: utf-8 -*-
"""
Reusable parallel execution helpers (e.g. bulk host checks).

Uses ThreadPoolExecutor + as_completed so callers can stream progress while
still receiving results indexed for stable final ordering.
"""

from __future__ import annotations

from mc_constants import DEFAULT_PARALLEL_MAX_WORKERS
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional, TypeVar

# Keep item type consistent between input list and worker arg.
T = TypeVar("T")
# Keep worker/on_complete/result list return types the same.
R = TypeVar("R")


def run_parallel_indexed(
    items: List[T],
    worker: Callable[[int, T], R],
    *,
    max_workers: int = DEFAULT_PARALLEL_MAX_WORKERS,
    on_complete: Optional[Callable[[R], None]] = None,
) -> List[R]:
    """
    Run "worker(index, item)" for each entry in "items" with a thread pool.

    "items" is the list of items to process, typically a list of hostnames or IP addresses.

    "worker" is the function that will be called for each item. It should take two arguments:
    the index of the item and the item itself.

    "max_workers" is the maximum number of workers to use.

    "on_complete" is the function that will be called when a task is complete.

    The returned list is in order "items" so callers can
    build a final summary (e.g. join "row[0]" per row) while still
    streaming progress in "on_complete".

    The worker's "index" argument is the position in "items"

    Workers should catch expected exceptions and return result objects; an
    uncaught exception in a worker will propagate from "future.result()".
    """
    n = len(items)
    if n == 0:
        return []
    workers = max(1, min(max_workers, n))
    results: dict[int, R] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {executor.submit(worker, i, items[i]): i for i in range(n)}
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            result = future.result()
            results[idx] = result
            if on_complete is not None:
                on_complete(result)
    return [results[i] for i in range(n)]
