from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from openclaw_yolo.models import ExperimentConfig, GoalConfig, TrialRecord
from openclaw_yolo.utils import utc_now_iso


class Repository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._memory_connection: sqlite3.Connection | None = None
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(self.db_path, check_same_thread=False)
                self._memory_connection.row_factory = sqlite3.Row
                self._configure_connection(self._memory_connection)
            return self._memory_connection
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        self._configure_connection(connection)
        return connection

    def _configure_connection(self, connection: sqlite3.Connection) -> None:
        for statement in (
            "PRAGMA journal_mode=MEMORY",
            "PRAGMA synchronous=OFF",
            "PRAGMA temp_store=MEMORY",
        ):
            try:
                connection.execute(statement)
            except sqlite3.OperationalError:
                continue

    def _ensure_schema(self) -> None:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL DEFAULT '',
                    session_key TEXT NOT NULL DEFAULT '',
                    task_type TEXT NOT NULL,
                    dataset_root TEXT NOT NULL,
                    dataset_yaml TEXT NOT NULL,
                    pretrained_model TEXT NOT NULL,
                    save_root TEXT NOT NULL,
                    goal_config TEXT NOT NULL,
                    status TEXT NOT NULL,
                    auto_iterate INTEGER NOT NULL,
                    confirm_timeout INTEGER NOT NULL,
                    initial_params TEXT NOT NULL,
                    search_space TEXT NOT NULL,
                    stop_conditions TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trials (
                    trial_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    iteration INTEGER NOT NULL,
                    params_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    run_dir TEXT NOT NULL,
                    summary_path TEXT,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'trained',
                    note TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id)
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT NOT NULL,
                    trial_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(experiments)").fetchall()
            }
            if "description" not in columns:
                conn.execute("ALTER TABLE experiments ADD COLUMN description TEXT NOT NULL DEFAULT ''")
            if "session_key" not in columns:
                conn.execute("ALTER TABLE experiments ADD COLUMN session_key TEXT NOT NULL DEFAULT ''")
            trial_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(trials)").fetchall()
            }
            if "source" not in trial_columns:
                conn.execute("ALTER TABLE trials ADD COLUMN source TEXT NOT NULL DEFAULT 'trained'")
            if "note" not in trial_columns:
                conn.execute("ALTER TABLE trials ADD COLUMN note TEXT NOT NULL DEFAULT ''")
            if "reason" not in trial_columns:
                conn.execute("ALTER TABLE trials ADD COLUMN reason TEXT NOT NULL DEFAULT ''")

    def _next_id(self, prefix: str, table: str, column: str) -> str:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {column} AS value FROM {table} WHERE {column} LIKE ?",
                (f"{prefix}_%",),
            ).fetchall()
        max_index = 0
        for row in rows:
            raw_value = row["value"]
            try:
                _, suffix = str(raw_value).rsplit("_", 1)
                max_index = max(max_index, int(suffix))
            except (ValueError, TypeError):
                continue
        return f"{prefix}_{max_index + 1:03d}"

    def next_experiment_id(self) -> str:
        return self._next_id("exp", "experiments", "experiment_id")

    def next_trial_id(self) -> str:
        return self._next_id("trial", "trials", "trial_id")

    def create_experiment(self, config: ExperimentConfig) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO experiments (
                    experiment_id, description, session_key, task_type, dataset_root, dataset_yaml, pretrained_model,
                    save_root, goal_config, status, auto_iterate, confirm_timeout,
                    initial_params, search_space, stop_conditions, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    config.experiment_id,
                    config.description,
                    config.session_key,
                    config.task_type,
                    config.dataset_root,
                    config.dataset_yaml,
                    config.pretrained_model,
                    config.save_root,
                    json.dumps(config.goal.__dict__),
                    config.status,
                    int(config.auto_iterate),
                    config.confirm_timeout,
                    json.dumps(config.initial_params),
                    json.dumps(config.search_space),
                    json.dumps(config.stop_conditions),
                    utc_now_iso(),
                ),
            )

    def get_experiment(self, experiment_id: str) -> ExperimentConfig:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"experiment not found: {experiment_id}")
        return ExperimentConfig(
            experiment_id=row["experiment_id"],
            description=row["description"],
            session_key=row["session_key"],
            task_type=row["task_type"],
            dataset_root=row["dataset_root"],
            dataset_yaml=row["dataset_yaml"],
            pretrained_model=row["pretrained_model"],
            save_root=row["save_root"],
            goal=GoalConfig(**json.loads(row["goal_config"])),
            auto_iterate=bool(row["auto_iterate"]),
            confirm_timeout=int(row["confirm_timeout"]),
            status=row["status"],
            initial_params=json.loads(row["initial_params"]),
            search_space=json.loads(row["search_space"]),
            stop_conditions=json.loads(row["stop_conditions"]),
        )

    def update_experiment_status(self, experiment_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE experiments SET status = ? WHERE experiment_id = ?",
                (status, experiment_id),
            )

    def delete_experiment(self, experiment_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM experiments WHERE experiment_id = ?", (experiment_id,))

    def list_experiments(self) -> list[ExperimentConfig]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM experiments ORDER BY created_at DESC, experiment_id DESC"
            ).fetchall()
        return [
            ExperimentConfig(
                experiment_id=row["experiment_id"],
                description=row["description"],
                session_key=row["session_key"],
                task_type=row["task_type"],
                dataset_root=row["dataset_root"],
                dataset_yaml=row["dataset_yaml"],
                pretrained_model=row["pretrained_model"],
                save_root=row["save_root"],
                goal=GoalConfig(**json.loads(row["goal_config"])),
                auto_iterate=bool(row["auto_iterate"]),
                confirm_timeout=int(row["confirm_timeout"]),
                status=row["status"],
                initial_params=json.loads(row["initial_params"]),
                search_space=json.loads(row["search_space"]),
                stop_conditions=json.loads(row["stop_conditions"]),
            )
            for row in rows
        ]

    def stale_unstarted_experiments(self, cutoff_iso: str, status: str) -> list[ExperimentConfig]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.*
                FROM experiments e
                LEFT JOIN trials t ON t.experiment_id = e.experiment_id
                WHERE e.status = ? AND e.created_at < ?
                GROUP BY e.experiment_id
                HAVING COUNT(t.trial_id) = 0
                ORDER BY e.created_at ASC, e.experiment_id ASC
                """,
                (status, cutoff_iso),
            ).fetchall()
        return [
            ExperimentConfig(
                experiment_id=row["experiment_id"],
                description=row["description"],
                session_key=row["session_key"],
                task_type=row["task_type"],
                dataset_root=row["dataset_root"],
                dataset_yaml=row["dataset_yaml"],
                pretrained_model=row["pretrained_model"],
                save_root=row["save_root"],
                goal=GoalConfig(**json.loads(row["goal_config"])),
                auto_iterate=bool(row["auto_iterate"]),
                confirm_timeout=int(row["confirm_timeout"]),
                status=row["status"],
                initial_params=json.loads(row["initial_params"]),
                search_space=json.loads(row["search_space"]),
                stop_conditions=json.loads(row["stop_conditions"]),
            )
            for row in rows
        ]

    def create_trial(self, trial: TrialRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trials (
                    trial_id, experiment_id, iteration, params_json, metrics_json, run_dir,
                    summary_path, status, source, note, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trial.trial_id,
                    trial.experiment_id,
                    trial.iteration,
                    json.dumps(trial.params),
                    json.dumps(trial.metrics),
                    trial.run_dir,
                    trial.summary_path,
                    trial.status,
                    trial.source,
                    trial.note,
                    trial.reason,
                    utc_now_iso(),
                ),
            )

    def update_trial(
        self,
        trial_id: str,
        *,
        status: str | None = None,
        metrics: dict[str, Any] | None = None,
        summary_path: str | None = None,
    ) -> None:
        assignments: list[str] = []
        values: list[Any] = []
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if metrics is not None:
            assignments.append("metrics_json = ?")
            values.append(json.dumps(metrics))
        if summary_path is not None:
            assignments.append("summary_path = ?")
            values.append(summary_path)
        if not assignments:
            return
        values.append(trial_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE trials SET {', '.join(assignments)} WHERE trial_id = ?",
                values,
            )

    def get_trial(self, trial_id: str) -> TrialRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM trials WHERE trial_id = ?",
                (trial_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"trial not found: {trial_id}")
        return TrialRecord(
            trial_id=row["trial_id"],
            experiment_id=row["experiment_id"],
            iteration=int(row["iteration"]),
            params=json.loads(row["params_json"]),
            status=row["status"],
            run_dir=row["run_dir"],
            summary_path=row["summary_path"],
            metrics=json.loads(row["metrics_json"]),
            source=row["source"],
            note=row["note"],
            reason=row["reason"],
        )

    def list_trials(self, experiment_id: str) -> list[TrialRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trials WHERE experiment_id = ? ORDER BY iteration ASC",
                (experiment_id,),
            ).fetchall()
        return [
            TrialRecord(
                trial_id=row["trial_id"],
                experiment_id=row["experiment_id"],
                iteration=int(row["iteration"]),
                params=json.loads(row["params_json"]),
                status=row["status"],
                run_dir=row["run_dir"],
                summary_path=row["summary_path"],
                metrics=json.loads(row["metrics_json"]),
                source=row["source"],
                note=row["note"],
                reason=row["reason"],
            )
            for row in rows
        ]

    def delete_trials_for_experiment(self, experiment_id: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM trials WHERE experiment_id = ?", (experiment_id,))
        return int(cursor.rowcount or 0)

    def delete_trial(self, trial_id: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM trials WHERE trial_id = ?", (trial_id,))
        return int(cursor.rowcount or 0)

    def add_event(
        self,
        experiment_id: str,
        event_type: str,
        payload: dict[str, Any],
        trial_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (experiment_id, trial_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (experiment_id, trial_id, event_type, json.dumps(payload), utc_now_iso()),
            )

    def delete_events_for_experiment(self, experiment_id: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM events WHERE experiment_id = ?", (experiment_id,))
        return int(cursor.rowcount or 0)

    def delete_events_for_trial(self, trial_id: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM events WHERE trial_id = ?", (trial_id,))
        return int(cursor.rowcount or 0)

    def latest_event(self, experiment_id: str, event_type: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json FROM events
                WHERE experiment_id = ? AND event_type = ?
                ORDER BY event_id DESC LIMIT 1
                """,
                (experiment_id, event_type),
            ).fetchone()
        return None if row is None else json.loads(row["payload_json"])

    def latest_event_for_types(
        self,
        experiment_id: str,
        event_types: list[str],
    ) -> dict[str, Any] | None:
        if not event_types:
            return None
        placeholders = ", ".join("?" for _ in event_types)
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT event_type, payload_json, created_at FROM events
                WHERE experiment_id = ? AND event_type IN ({placeholders})
                ORDER BY event_id DESC LIMIT 1
                """,
                (experiment_id, *event_types),
            ).fetchone()
        if row is None:
            return None
        return {
            "event_type": row["event_type"],
            "payload": json.loads(row["payload_json"]),
            "created_at": row["created_at"],
        }

    def recent_summaries(self, experiment_id: str, limit: int = 3) -> list[dict[str, Any]]:
        trials = [trial for trial in self.list_trials(experiment_id) if trial.summary_path]
        summaries: list[dict[str, Any]] = []
        for trial in trials[-limit:]:
            if trial.summary_path and Path(trial.summary_path).exists():
                summaries.append(json.loads(Path(trial.summary_path).read_text(encoding="utf-8")))
        return summaries
