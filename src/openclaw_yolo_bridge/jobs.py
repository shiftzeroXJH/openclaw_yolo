from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock, Thread
from typing import Any, Callable
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class BridgeJob:
    job_id: str
    kind: str
    experiment_id: str
    status: str
    created_at: str
    updated_at: str
    result: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, BridgeJob] = {}
        self._lock = Lock()

    def start(self, kind: str, experiment_id: str, target: Callable[[], dict[str, Any]]) -> BridgeJob:
        now = _utc_now()
        job = BridgeJob(
            job_id=f"job_{uuid4().hex}",
            kind=kind,
            experiment_id=experiment_id,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.job_id] = job

        def runner() -> None:
            self._update(job.job_id, status="running")
            try:
                result = target()
                self._update(job.job_id, status="completed", result=result)
            except Exception as exc:  # pragma: no cover
                self._update(job.job_id, status="failed", error=str(exc))

        Thread(target=runner, daemon=True).start()
        return job

    def get(self, job_id: str) -> BridgeJob:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"job not found: {job_id}")
            return self._jobs[job_id]

    def _update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if status is not None:
                job.status = status
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = _utc_now()
