"""Thread-backed worker pool. Depth inference releases the GIL via ORT;
render I/O is the bottleneck, so threads beat processes here."""
from __future__ import annotations

import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future

from hologram_studio.config.settings import Settings
from hologram_studio.workers.jobs import RenderJob
from hologram_studio.workers.pipeline import run_pipeline

log = logging.getLogger(__name__)


class WorkerPool:
    def __init__(self, settings: Settings, size: int = 2) -> None:
        if size < 1:
            raise ValueError("worker pool size must be >= 1")
        self._settings = settings
        self._size = size
        self._queue: queue.Queue[RenderJob] = queue.Queue()
        self._executor = ThreadPoolExecutor(max_workers=size, thread_name_prefix="hps-worker")
        self._futures: list[Future] = []
        self._lock = threading.Lock()
        self._running = True

    def submit(self, job: RenderJob) -> None:
        with self._lock:
            if not self._running:
                raise RuntimeError("pool is shut down")
            self._queue.put(job)

    def drain(self) -> None:
        """Run queued jobs to completion. Blocks until the queue is empty."""
        while not self._queue.empty():
            job = self._queue.get_nowait()
            fut = self._executor.submit(self._run_one, job)
            with self._lock:
                self._futures.append(fut)
        for fut in self._futures:
            fut.result()

    def _run_one(self, job: RenderJob) -> None:
        while True:
            try:
                run_pipeline(job, self._settings)
                log.info("job %s done", job.id)
                return
            except Exception:
                job.next_attempt()
                if job.exhausted:
                    log.exception("job %s exhausted after %d attempts", job.id, job.attempts)
                    raise
                log.warning("job %s retry %d/%d", job.id, job.attempts, job.max_attempts)

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
        self._executor.shutdown(wait=True, cancel_futures=False)