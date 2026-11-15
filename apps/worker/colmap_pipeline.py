"""COLMAP adapter for deterministic camera-pose and sparse reconstruction.

COLMAP is an optional external executable. CI tests this adapter with a mocked
process; a real run requires COLMAP installed on the worker host/container.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable


REQUIRED_SPARSE_FILES = ("cameras.bin", "images.bin", "points3D.bin")


class ColmapError(RuntimeError):
    """Raised when COLMAP is unavailable or reconstruction fails."""


def run_colmap_sparse_reconstruction(
    image_dir: str | Path,
    output_dir: str | Path,
    *,
    executable: str = "colmap",
    runner: Callable = subprocess.run,
) -> dict:
    """Run feature extraction, sequential matching, and mapper in fixed order."""
    binary = shutil.which(executable)
    if not binary:
        raise ColmapError(
            "COLMAP executable not found. Install COLMAP and make its 'colmap' "
            "command available on PATH before running camera-pose estimation."
        )

    images = Path(image_dir).resolve()
    output = Path(output_dir).resolve()
    if not images.is_dir() or not any(images.glob("*.jpg")):
        raise ColmapError(f"No JPG source frames found in {images}")

    output.mkdir(parents=True, exist_ok=True)
    database = output / "database.db"
    sparse_dir = output / "sparse"
    sparse_dir.mkdir(exist_ok=True)

    commands = [
        [
            binary, "feature_extractor",
            "--database_path", str(database),
            "--image_path", str(images),
            "--ImageReader.single_camera", "1",
        ],
        [
            binary, "sequential_matcher",
            "--database_path", str(database),
        ],
        [
            binary, "mapper",
            "--database_path", str(database),
            "--image_path", str(images),
            "--output_path", str(sparse_dir),
        ],
    ]

    # Colab and other cloud workers are headless. Force Qt-based COLMAP builds
    # to use their offscreen platform plugin instead of trying to open a display.
    colmap_env = os.environ.copy()
    colmap_env.setdefault("QT_QPA_PLATFORM", "offscreen")

    for command in commands:
        try:
            runner(command, capture_output=True, text=True, check=True, timeout=3600, env=colmap_env)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ColmapError(
                f"COLMAP stage '{command[1]}' failed: {getattr(exc, 'stderr', '') or exc}"
            ) from exc

    models = sorted(path for path in sparse_dir.iterdir() if path.is_dir())
    valid_model = None
    for model in models:
        if all((model / filename).is_file() and (model / filename).stat().st_size > 0
               for filename in REQUIRED_SPARSE_FILES):
            valid_model = model
            break
    if valid_model is None:
        raise ColmapError(
            "COLMAP completed but no valid sparse model was produced "
            "(expected cameras.bin, images.bin, and points3D.bin)."
        )

    image_count = len(list(images.glob("*.jpg")))
    metadata = {
        "schema_version": 1,
        "stage": "colmap_sparse_reconstruction",
        "status": "sparse_reconstruction_ready_gsplat_required",
        "camera_model": "SIMPLE_RADIAL",
        "source_image_count": image_count,
        "registered_image_count": None,
        "sparse_model_directory": str(valid_model),
        "sparse_model_files": list(REQUIRED_SPARSE_FILES),
        "world_ready": False,
        "next_stage": "gaussian_splat_training_and_spz_export",
    }
    (output / "colmap-manifest.json").write_text(json.dumps(metadata, indent=2))
    return metadata
