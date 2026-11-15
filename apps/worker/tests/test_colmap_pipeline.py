import subprocess
from pathlib import Path

import pytest

from colmap_pipeline import ColmapError, run_colmap_sparse_reconstruction


def test_runs_colmap_commands_in_expected_order(monkeypatch, tmp_path):
    images = tmp_path / "frames"
    images.mkdir()
    (images / "frame-000001.jpg").write_bytes(b"frame1")
    (images / "frame-000002.jpg").write_bytes(b"frame2")
    output = tmp_path / "colmap"
    calls = []

    monkeypatch.setattr("colmap_pipeline.shutil.which", lambda name: "/usr/bin/colmap")

    def fake_run(command, **kwargs):
        calls.append(command[1])
        if command[1] == "mapper":
            model = output / "sparse" / "0"
            model.mkdir(parents=True)
            for name in ("cameras.bin", "images.bin", "points3D.bin"):
                (model / name).write_bytes(b"valid")
        return subprocess.CompletedProcess(command, 0, "", "")

    result = run_colmap_sparse_reconstruction(images, output, runner=fake_run)

    assert calls == ["feature_extractor", "sequential_matcher", "mapper"]
    assert result["source_image_count"] == 2
    assert result["status"] == "sparse_reconstruction_ready_gsplat_required"
    assert result["world_ready"] is False
    assert (output / "colmap-manifest.json").is_file()


def test_missing_colmap_binary_has_actionable_error(monkeypatch, tmp_path):
    images = tmp_path / "frames"
    images.mkdir()
    (images / "frame.jpg").write_bytes(b"frame")
    monkeypatch.setattr("colmap_pipeline.shutil.which", lambda name: None)

    with pytest.raises(ColmapError, match="Install COLMAP"):
        run_colmap_sparse_reconstruction(images, tmp_path / "out")


def test_colmap_failure_stops_pipeline(monkeypatch, tmp_path):
    images = tmp_path / "frames"
    images.mkdir()
    (images / "frame.jpg").write_bytes(b"frame")
    monkeypatch.setattr("colmap_pipeline.shutil.which", lambda name: "/usr/bin/colmap")

    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(1, command, stderr="feature extraction error")

    with pytest.raises(ColmapError, match="feature_extractor"):
        run_colmap_sparse_reconstruction(images, tmp_path / "out", runner=fail)


def test_rejects_empty_sparse_output(monkeypatch, tmp_path):
    images = tmp_path / "frames"
    images.mkdir()
    (images / "frame.jpg").write_bytes(b"frame")
    output = tmp_path / "out"
    monkeypatch.setattr("colmap_pipeline.shutil.which", lambda name: "/usr/bin/colmap")

    def fake_run(command, **kwargs):
        if command[1] == "mapper":
            (output / "sparse" / "0").mkdir(parents=True)
        return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(ColmapError, match="no valid sparse model"):
        run_colmap_sparse_reconstruction(images, output, runner=fake_run)
