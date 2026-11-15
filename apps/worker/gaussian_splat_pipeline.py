"""GPU-only Gaussian Splat training/export adapter.

The adapter deliberately delegates the version-sensitive training loop to an
installed gsplat-compatible trainer command. It validates every boundary and
never treats a PLY intermediate as a published browser world.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Callable


class SplatPipelineError(RuntimeError):
    """Raised when GPU training or asset export cannot safely proceed."""


def run_gaussian_splat_pipeline(
    images_dir: str | Path,
    colmap_dir: str | Path,
    output_dir: str | Path,
    *,
    trainer_command: str | None = None,
    exporter_command: str | None = None,
    runner: Callable = subprocess.run,
) -> dict:
    images = Path(images_dir).resolve()
    colmap = Path(colmap_dir).resolve()
    output = Path(output_dir).resolve()

    if not images.is_dir() or not any(images.glob("*.jpg")):
        raise SplatPipelineError("Training requires extracted JPG source frames.")
    if not colmap.is_dir() or not all((colmap / name).is_file() for name in
                                      ("cameras.bin", "images.bin", "points3D.bin")):
        raise SplatPipelineError("Training requires a validated COLMAP sparse model.")

    try:
        import torch
        import gsplat  # noqa: F401
    except ImportError as exc:
        raise SplatPipelineError(
            "Install the optional PyTorch CUDA and gsplat dependencies in the GPU worker."
        ) from exc
    if not torch.cuda.is_available():
        raise SplatPipelineError("A compatible NVIDIA CUDA GPU is required for Gaussian Splat training.")

    trainer = trainer_command or os.getenv("GSPLAT_TRAIN_COMMAND", "")
    exporter = exporter_command or os.getenv("SPLAT_EXPORT_COMMAND", "")
    if not trainer:
        raise SplatPipelineError(
            "Set GSPLAT_TRAIN_COMMAND to an installed gsplat training entry point."
        )
    if not exporter:
        raise SplatPipelineError(
            "Set SPLAT_EXPORT_COMMAND to a verified PLY-to-SPZ exporter."
        )

    output.mkdir(parents=True, exist_ok=True)
    ply = output / "scene.ply"
    spz = output / "scene.spz"
    commands = [
        shlex.split(trainer) + ["--images", str(images), "--colmap", str(colmap),
                                "--output", str(ply)],
        shlex.split(exporter) + [str(ply), str(spz)],
    ]
    for command in commands:
        try:
            runner(command, capture_output=True, text=True, check=True, timeout=86400)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise SplatPipelineError(
                f"Gaussian Splat stage '{Path(command[0]).name}' failed: "
                f"{getattr(exc, 'stderr', '') or exc}"
            ) from exc

    if not ply.is_file() or ply.stat().st_size == 0:
        raise SplatPipelineError("Training did not produce a non-empty scene.ply file.")
    if not spz.is_file() or spz.stat().st_size == 0:
        raise SplatPipelineError("Exporter did not produce a non-empty scene.spz file.")

    return {
        "schema_version": 1,
        "status": "world_ready",
        "world_asset_path": str(spz),
        "intermediate_ply_path": str(ply),
        "world_asset_format": "spz",
        "world_ready": True,
    }
