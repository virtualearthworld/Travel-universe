import sys
import types
import subprocess

import pytest

from gaussian_splat_pipeline import SplatPipelineError, run_gaussian_splat_pipeline


def _inputs(tmp_path):
    images = tmp_path / "frames"
    images.mkdir()
    (images / "frame-000001.jpg").write_bytes(b"frame")
    colmap = tmp_path / "sparse"
    colmap.mkdir()
    for name in ("cameras.bin", "images.bin", "points3D.bin"):
        (colmap / name).write_bytes(b"model")
    return images, colmap


def test_requires_cuda_and_gsplat_before_running(monkeypatch, tmp_path):
    images, colmap = _inputs(tmp_path)
    torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "gsplat", types.ModuleType("gsplat"))

    with pytest.raises(SplatPipelineError, match="CUDA GPU"):
        run_gaussian_splat_pipeline(images, colmap, tmp_path / "out")


def test_validates_real_spz_output_and_reports_world_ready(monkeypatch, tmp_path):
    images, colmap = _inputs(tmp_path)
    torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "gsplat", types.ModuleType("gsplat"))

    def fake_run(command, **kwargs):
        if command[0] == "trainer":
            (tmp_path / "out").mkdir(exist_ok=True)
            (tmp_path / "out" / "scene.ply").write_bytes(b"ply-data")
        else:
            (tmp_path / "out" / "scene.spz").write_bytes(b"spz-data")
        return subprocess.CompletedProcess(command, 0, "", "")

    result = run_gaussian_splat_pipeline(
        images, colmap, tmp_path / "out",
        trainer_command="trainer", exporter_command="exporter", runner=fake_run,
    )
    assert result["status"] == "world_ready"
    assert result["world_ready"] is True
    assert (tmp_path / "out" / "scene.spz").stat().st_size > 0


def test_never_marks_world_ready_without_spz(monkeypatch, tmp_path):
    images, colmap = _inputs(tmp_path)
    torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "gsplat", types.ModuleType("gsplat"))

    def no_export(command, **kwargs):
        if command[0] == "trainer":
            (tmp_path / "out").mkdir(exist_ok=True)
            (tmp_path / "out" / "scene.ply").write_bytes(b"ply-data")
        return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(SplatPipelineError, match="scene.spz"):
        run_gaussian_splat_pipeline(
            images, colmap, tmp_path / "out",
            trainer_command="trainer", exporter_command="exporter", runner=no_export,
        )


def test_rejects_missing_sparse_model(tmp_path):
    images = tmp_path / "frames"
    images.mkdir()
    (images / "frame.jpg").write_bytes(b"frame")
    with pytest.raises(SplatPipelineError, match="COLMAP sparse model"):
        run_gaussian_splat_pipeline(images, tmp_path / "missing", tmp_path / "out")
