from app import build_reconstruction_chain


def test_reconstruction_chain_runs_colmap_before_gpu_training():
    workflow = build_reconstruction_chain(
        "video-123",
        "reconstruction-inputs/video-123/inputs.zip",
    )

    assert [task.name for task in workflow.tasks] == [
        "reconstruction.estimate_camera_poses",
        "reconstruction.train_gaussian_splats",
    ]
    assert workflow.tasks[0].args == (
        "video-123",
        "reconstruction-inputs/video-123/inputs.zip",
    )
    assert workflow.tasks[1].options["queue"] == "gpu"


def test_reconstruction_chain_keeps_gpu_stage_separate():
    workflow = build_reconstruction_chain("video-456", "inputs.zip")

    assert workflow.tasks[0].options.get("queue") is None
    assert workflow.tasks[1].options["queue"] == "gpu"
