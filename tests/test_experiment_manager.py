from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openclaw_yolo.service import OrchestratorService, ServiceError
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

    assert result["trial_id"] == "trial_001"
    assert result["final_metrics"]["map50_95"] == 0.44
    assert service.repo.get_trial("trial_001").reason == "manual sweep"


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

    assert comparison["best_trial"]["trial_id"] == "trial_002"
    assert comparison["rows"][1]["is_best"] is True
    assert comparison["rows"][1]["delta_map50_95"] == 0.21
    assert comparison["rows"][1]["source"] == "imported"


def test_api_experiment_flow(tmp_path: Path) -> None:
    app_module.service = OrchestratorService(db_path=":memory:")
    client = TestClient(app_module.app)
    dataset_root = tmp_path / "dataset"
    _write_dataset(dataset_root)
    run_dir = tmp_path / "api-run"
    _write_results(run_dir, map50_95=0.47)

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

    comparison_response = client.get(f"/api/experiments/{experiment_id}/comparison")
    assert comparison_response.status_code == 200
    assert comparison_response.json()["rows"][0]["note"] == "api import"
