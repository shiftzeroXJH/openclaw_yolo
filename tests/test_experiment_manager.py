from __future__ import annotations

from pathlib import Path
from threading import Event

import pytest
from fastapi.testclient import TestClient

from openclaw_yolo.service import OrchestratorService, ServiceError
from openclaw_yolo.core.trainer import TrainingCancelledError
from openclaw_yolo_bridge import app as app_module


def _write_dataset(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    yaml_path = root / "data.yaml"
    yaml_path.write_text("path: .\ntrain: images/train\nval: images/val\nnames: []\n", encoding="utf-8")
    return yaml_path


def _write_results(run_dir: Path, map50_95: float = 0.42) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir.joinpath("results.csv").write_text(
        "\n".join(
            [
                "epoch,time,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),train/box_loss,val/box_loss,gpu_mem",
                f"1,1.5,0.50,0.40,0.55,{map50_95 - 0.02:.4f},1.2,1.4,2048",
                f"2,1.4,0.60,0.50,0.65,{map50_95:.4f},0.9,1.1,2048",
            ]
        ),
        encoding="utf-8",
    )


def _create_experiment(service: OrchestratorService, tmp_path: Path) -> str:
    dataset_root = tmp_path / "dataset"
    _write_dataset(dataset_root)
    result = service.create_experiment(
        description="local experiment",
        task_type="detection",
        dataset_root=str(dataset_root),
        dataset_yaml=None,
        pretrained="missing-ok.pt",
        save_root=str(tmp_path / "runs"),
        goal={"metric": "map50_95", "target": 0.9},
        initial_params={"imgsz": 224, "batch": 8, "epochs": 2, "workers": 0},
    )
    return result["experiment_id"]


def test_create_experiment_without_session_key(tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)

    detail = service.get_experiment_detail(experiment_id)

    assert detail["experiment"]["session_key"] == ""
    assert detail["experiment"]["task_type"] == "detection"
    assert detail["latest_params"]["imgsz"] == 224


def test_local_run_allows_many_valid_param_changes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)

    def fake_run_training(**kwargs):
        run_dir = Path(kwargs["run_dir"])
        _write_results(run_dir, map50_95=0.44)
        return {
            "run_dir": str(run_dir),
            "stdout_log": str(run_dir / "stdout.log"),
            "stderr_log": str(run_dir / "stderr.log"),
        }

    monkeypatch.setattr("openclaw_yolo.service.run_training", fake_run_training)
    params = service.get_param_metadata(experiment_id)["latest_params"]
    params.update(
        {
            "imgsz": 320,
            "batch": 16,
            "epochs": 3,
            "lr0": 0.005,
            "mosaic": 0.3,
        }
    )
    result = service.run_trial(experiment_id, params=params, reason="manual sweep")

    assert result["trial_id"] == "missing_ok_320_1"
    assert result["final_metrics"]["map50_95"] == 0.44
    assert service.repo.get_trial("missing_ok_320_1").reason == "manual sweep"


def test_local_run_returns_cancelled_when_training_is_stopped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)

    def fake_run_training(**_kwargs):
        raise TrainingCancelledError("training cancelled by user")

    monkeypatch.setattr("openclaw_yolo.service.run_training", fake_run_training)
    result = service.run_trial(experiment_id)

    assert result["status"] == "CANCELLED"
    trial = service.repo.list_trials(experiment_id)[0]
    assert trial.status == "CANCELLED"
    assert service.repo.get_experiment(experiment_id).status == "CANCELLED"


def test_cancel_task_reports_process_termination(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)
    terminated = Event()

    monkeypatch.setattr("openclaw_yolo.service.cancel_training_process", lambda key: terminated.set() or key == experiment_id)
    response = service.cancel_task(experiment_id, "user stopped")

    assert terminated.is_set()
    assert response["status"] == "CANCELLED"
    assert response["process_terminated"] is True
    assert response["reason"] == "user stopped"


def test_openclaw_continue_keeps_three_param_limit(tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)
    imported_run = tmp_path / "external-run"
    _write_results(imported_run, map50_95=0.2)
    service.import_run(experiment_id, run_dir=str(imported_run), note="baseline import")

    with pytest.raises(ServiceError, match="no more than 3 params"):
        service.continue_experiment(
            experiment_id,
            param_updates={"imgsz": 320, "batch": 16, "epochs": 3, "lr0": 0.005},
            reason="too many updates",
        )


def test_import_run_generates_comparison_row(tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)
    first = tmp_path / "run-a"
    second = tmp_path / "run-b"
    _write_results(first, map50_95=0.31)
    _write_results(second, map50_95=0.52)

    service.import_run(experiment_id, run_dir=str(first), note="low score")
    service.import_run(experiment_id, run_dir=str(second), note="better score")
    comparison = service.compare_experiment(experiment_id)

    assert comparison["best_trial"]["trial_id"] == "missing_ok_224_2"
    assert comparison["rows"][1]["is_best"] is True
    assert comparison["rows"][1]["delta_map50_95"] == 0.21
    assert comparison["rows"][1]["source"] == "imported"
    assert comparison["rows"][1]["model_display"] == "missing-ok.pt"


def test_remote_trial_register_and_sync_running_csv(tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)
    server_id = service.create_remote_server(
        name="gpu-a",
        host="fake-host",
        username="trainer",
        auth_type="key",
        private_key_path="~/.ssh/id_rsa",
    )["remote_server"]["remote_server_id"]
    args_yaml = "\n".join(
        [
            r"model: D:\project\openclaw_yolo\src\openclaw_yolo\models\yolo26n.pt",
            "imgsz: 224",
            "batch: 8",
            "epochs: 3",
            "workers: 0",
            "lr0: 0.01",
            "weight_decay: 0.0005",
            "mosaic: 0.5",
            "mixup: 0.0",
            "degrees: 0.0",
            "translate: 0.1",
            "scale: 0.5",
            "fliplr: 0.5",
            "hsv_h: 0.015",
            "hsv_s: 0.7",
            "hsv_v: 0.4",
        ]
    )
    results_csv = "\n".join(
        [
            "epoch,time,metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),train/box_loss,val/box_loss,gpu_mem",
            "1,1.5,0.50,0.40,0.55,0.31,1.2,1.4,2048",
            "2,1.4,0.60,0.50,0.65,0.42,0.9,1.1,2048",
        ]
    )
    files = {
        "/runs/train/args.yaml": args_yaml,
        "/runs/train/results.csv": results_csv,
    }

    class FakeAttr:
        def __init__(self, filename: str = "", size: int = 0, mtime: float = 0.0) -> None:
            self.filename = filename
            self.st_size = size
            self.st_mtime = mtime

    class FakeHandle:
        def __init__(self, text: str) -> None:
            self.text = text

        def read(self) -> bytes:
            return self.text.encode("utf-8")

        def __enter__(self) -> "FakeHandle":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    class FakeSftp:
        def open(self, path: str, _mode: str) -> FakeHandle:
            return FakeHandle(files[path])

        def stat(self, path: str) -> FakeAttr:
            return FakeAttr(size=len(files[path]), mtime=1.0)

        def get(self, remote: str, local: str) -> None:
            Path(local).write_text(files[remote], encoding="utf-8")

        def listdir_attr(self, _remote_dir: str) -> list[FakeAttr]:
            return []

        def close(self) -> None:
            return None

    class FakeClient:
        def close(self) -> None:
            return None

    service._open_sftp = lambda _server: (FakeClient(), FakeSftp())  # type: ignore[method-assign]
    registered = service.register_remote_trial(
        experiment_id,
        remote_server_id=server_id,
        remote_run_dir="/runs/train",
    )
    synced = service.sync_remote_trial(registered["trial_id"])

    assert registered["trial_id"] == "yolo26n_224_1"
    assert Path(registered["local_run_dir"]).parent.name == experiment_id
    assert synced["remote_training_status"] == "running"
    assert synced["epoch_count"] == 2
    assert synced["final_metrics"]["map50_95"] == 0.42


def test_import_remote_run_returns_registered_trial_on_sync_failure(tmp_path: Path) -> None:
    service = OrchestratorService(db_path=":memory:")
    experiment_id = _create_experiment(service, tmp_path)
    server_id = service.create_remote_server(
        name="gpu-a",
        host="fake-host",
        username="trainer",
        auth_type="key",
        private_key_path="~/.ssh/id_rsa",
    )["remote_server"]["remote_server_id"]
    args_yaml = "\n".join(
        [
            "model: yolo26n.pt",
            "imgsz: 224",
            "batch: 8",
            "epochs: 3",
            "workers: 0",
        ]
    )
    files = {"/runs/train/args.yaml": args_yaml}

    class FakeHandle:
        def __init__(self, text: str) -> None:
            self.text = text

        def read(self) -> bytes:
            return self.text.encode("utf-8")

        def __enter__(self) -> "FakeHandle":
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    class FakeSftp:
        def open(self, path: str, _mode: str) -> FakeHandle:
            return FakeHandle(files[path])

        def stat(self, path: str) -> object:
            raise OSError(f"missing {path}")

        def get(self, remote: str, local: str) -> None:
            Path(local).write_text(files[remote], encoding="utf-8")

        def close(self) -> None:
            return None

    class FakeClient:
        def close(self) -> None:
            return None

    service._open_sftp = lambda _server: (FakeClient(), FakeSftp())  # type: ignore[method-assign]
    result = service.import_remote_run(
        experiment_id,
        remote_server_id=server_id,
        remote_run_dir="/runs/train",
    )

    assert result["sync_status"] == "failed"
    assert result["registered"]["trial_id"] == "yolo26n_224_1"
    assert service.repo.get_trial("yolo26n_224_1").sync_status == "failed"


def test_api_experiment_flow(tmp_path: Path) -> None:
    app_module.service = OrchestratorService(db_path=":memory:")
    client = TestClient(app_module.app)
    dataset_root = tmp_path / "dataset"
    _write_dataset(dataset_root)
    run_dir = tmp_path / "api-run"
    second_run_dir = tmp_path / "api-run-2"
    _write_results(run_dir, map50_95=0.47)
    _write_results(second_run_dir, map50_95=0.58)

    create_response = client.post(
        "/api/experiments",
        json={
            "description": "api experiment",
            "task_type": "detection",
            "dataset_root": str(dataset_root),
            "pretrained": "missing-ok.pt",
            "save_root": str(tmp_path / "runs"),
            "goal": {"metric": "map50_95", "target": 0.8},
            "initial_params": {"imgsz": 224, "batch": 8, "epochs": 2},
        },
    )
    assert create_response.status_code == 200
    experiment_id = create_response.json()["experiment_id"]

    rename_response = client.patch(
        f"/api/experiments/{experiment_id}",
        json={"description": "renamed api experiment"},
    )
    assert rename_response.status_code == 200
    assert rename_response.json()["experiment"]["description"] == "renamed api experiment"

    detail_response = client.get(f"/api/experiments/{experiment_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["experiment"]["description"] == "renamed api experiment"

    list_after_rename = client.get("/api/experiments")
    assert list_after_rename.status_code == 200
    assert list_after_rename.json()["experiments"][0]["description"] == "renamed api experiment"

    params_response = client.get(f"/api/experiments/{experiment_id}/params")
    assert params_response.status_code == 200
    assert params_response.json()["latest_params"]["imgsz"] == 224

    invalid_response = client.post(
        f"/api/experiments/{experiment_id}/params/validate",
        json={"param_updates": {"imgsz": 225}},
    )
    assert invalid_response.status_code == 200
    assert invalid_response.json()["valid"] is False

    import_response = client.post(
        f"/api/experiments/{experiment_id}/trials/import",
        json={"run_dir": str(run_dir), "note": "api import"},
    )
    assert import_response.status_code == 200
    first_trial_id = import_response.json()["trial_id"]

    second_import_response = client.post(
        f"/api/experiments/{experiment_id}/trials/import",
        json={"run_dir": str(second_run_dir), "note": "api import 2"},
    )
    assert second_import_response.status_code == 200
    second_trial_id = second_import_response.json()["trial_id"]

    comparison_response = client.get(f"/api/experiments/{experiment_id}/comparison")
    assert comparison_response.status_code == 200
    assert comparison_response.json()["rows"][0]["note"] == "api import"
    assert len(comparison_response.json()["rows"]) == 2

    delete_trial_response = client.delete(f"/api/trials/{first_trial_id}?keep_files=true")
    assert delete_trial_response.status_code == 200
    assert delete_trial_response.json()["deleted"] is True
    assert delete_trial_response.json()["remaining_trial_count"] == 1

    comparison_after_trial_delete = client.get(f"/api/experiments/{experiment_id}/comparison")
    assert comparison_after_trial_delete.status_code == 200
    rows = comparison_after_trial_delete.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["trial_id"] == second_trial_id

    blocked_delete = client.delete(f"/api/experiments/{experiment_id}?keep_files=true")
    assert blocked_delete.status_code == 400

    cancel_response = client.post(
        f"/api/experiments/{experiment_id}/cancel",
        json={"reason": "api stop"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"

    delete_response = client.delete(f"/api/experiments/{experiment_id}?keep_files=true&force=true")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert delete_response.json()["kept_files"] is True

    list_response = client.get("/api/experiments")
    assert list_response.status_code == 200
    assert list_response.json()["experiments"] == []
