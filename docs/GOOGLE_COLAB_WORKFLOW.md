# Google Colab reconstruction workflow (iPad-first)

## Purpose and honest operating model

Travel Universe's current worker code already separates frame preparation, COLMAP sparse reconstruction, and CUDA/gsplat training. Its COLMAP and Gaussian Splat adapters are real command wrappers, but the project does not currently bundle a complete trainer command or a persistent public GPU backend.

This guide uses **Google Colab as a manually started, temporary reconstruction runner** controlled from the iPad. It is not a continuously available backend: a free Colab runtime can be unavailable, disconnected, or terminated. The free tier does not guarantee a T4 or any particular GPU, and its resource limits change. Save important inputs, checkpoints, and outputs to Google Drive during the run.

The first integration milestone is to process the same private source video through COLMAP, gsplat training, and SPZ export in Colab. Only after a real SPZ is produced and the viewer loads it should the app report `world_ready`.

## Architecture

- **GitHub (this repository):** source code, worker adapters, and this guide.
- **iPad browser:** GitHub editing/review, Google Colab controls, Drive file selection, and Travel Universe viewer.
- **Google Colab:** temporary CPU/GPU execution for FFmpeg, COLMAP, and gsplat.
- **Google Drive:** private source videos, extracted frames, COLMAP output, checkpoints, and final SPZ files.
- **Travel Universe viewer:** loads a validated SPZ URL. The current public GitHub Pages site is static and cannot call a Colab runtime as a durable API.

No private video, generated scene, access token, or secret belongs in this public repository.

## 1. Open Colab on the iPad

1. Open Safari and visit https://colab.research.google.com/.
2. Sign in with your Google account.
3. Choose **New notebook**.
4. In the notebook, open **Runtime → Change runtime type**.
5. Choose **T4 GPU** if it is offered, then save.
6. Run this first cell:

```python
import torch, subprocess
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    subprocess.run(["nvidia-smi"], check=False)
else:
    raise RuntimeError("No GPU was assigned. Reconnect later or use CPU only for preprocessing/COLMAP.")
```

A T4 is an availability-dependent option, not a guaranteed free resource. Do not purchase Colab compute for this project.

## 2. Connect persistent Google Drive storage

Run:

```python
from google.colab import drive
drive.mount('/content/drive')
```

Approve Google's Drive permission prompt. Create a project folder:

```python
from pathlib import Path
ROOT = Path('/content/drive/MyDrive/TravelUniverse')
ROOT.mkdir(parents=True, exist_ok=True)
print(ROOT)
```

Use Drive for persistent files because the Colab VM's local disk is temporary.

## 3. Clone the existing GitHub repository

The repository is public, so cloning it does not require a GitHub token:

```bash
!git clone https://github.com/virtualearthworld/Travel-universe.git /content/Travel-universe
!git -C /content/Travel-universe log -1 --oneline
```

This gives the notebook access to the actual Travel Universe worker adapters. Do not upload your private video to GitHub.

## 4. Upload the original video privately

Use the Colab file picker (on iPad, select the video from Files or Photos when offered):

```python
from google.colab import files
uploaded = files.upload()
```

Choose the original travel video. Copy it into Drive so it survives a runtime reset:

```python
import shutil
from pathlib import Path
name = next(iter(uploaded))
source_video = ROOT / name
shutil.copy2(name, source_video)
print("Saved privately to:", source_video)
```

The previously prepared Travel Universe test clip was a 19.8-second, 1920×1080 MOV. Use that same original clip for the first end-to-end validation, not a replacement sample. The user must select it from their own iPad/Drive when starting the notebook; it is not stored in GitHub.

## 5. Install and verify FFmpeg and COLMAP

Start with the Colab Ubuntu packages:

```bash
!apt-get update -qq
!apt-get install -y ffmpeg colmap
!ffmpeg -version | head -n 1
!colmap -h | head -n 8
```

If the Colab image does not offer a working `colmap` package, stop here and use the current official COLMAP installation guidance: https://colmap.github.io/install.html. Do not continue to training without a working COLMAP executable.

## 6. Extract frames using the Travel Universe sampling convention

The current worker samples two frames per second and caps the long image edge at 1600 pixels. Use the same convention:

```python
import subprocess
DATA = Path('/content/tu_dataset')
IMAGES = DATA / 'images'
IMAGES.mkdir(parents=True, exist_ok=True)
subprocess.run([
    'ffmpeg','-hide_banner','-loglevel','error','-i',str(source_video),
    '-map','0:v:0','-vf',"fps=2,scale='min(1600,iw)':-2",
    '-q:v','2',str(IMAGES/'frame-%06d.jpg')
], check=True)
frames = sorted(IMAGES.glob('*.jpg'))
print("Extracted frames:", len(frames))
assert len(frames) >= 2, "Not enough frames were extracted"
```

Persist the frames in Drive if you need to resume after a Colab disconnect:

```python
import shutil
DRIVE_DATA = ROOT / 'dataset'
if DRIVE_DATA.exists():
    shutil.rmtree(DRIVE_DATA)
shutil.copytree(DATA, DRIVE_DATA)
```

## 7. Run the repository's COLMAP adapter

The repository adapter runs feature extraction, sequential matching, and mapping, then checks for the three required sparse-model files. It is safer to use that adapter than to mark a job successful just because the COLMAP process returned.

```python
import sys
sys.path.insert(0, '/content/Travel-universe/apps/worker')
from colmap_pipeline import run_colmap_sparse_reconstruction

colmap_result = run_colmap_sparse_reconstruction(
    image_dir=IMAGES,
    output_dir=DATA / 'colmap'
)
print(colmap_result)
assert colmap_result['status'] == 'sparse_reconstruction_ready_gsplat_required'
```

A successful COLMAP result is **not yet a 3D world**. It means camera poses and a sparse model are ready for Gaussian Splat training.

Prepare the directory expected by the gsplat COLMAP dataset loader:

```python
sparse_candidates = sorted((DATA / 'colmap' / 'sparse').glob('*'))
model_dir = next((p for p in sparse_candidates if p.is_dir() and
                  all((p / f).is_file() for f in
                      ['cameras.bin','images.bin','points3D.bin'])), None)
assert model_dir is not None, "No valid COLMAP sparse model found"
(DATA / 'sparse').mkdir(exist_ok=True)
shutil.copytree(model_dir, DATA / 'sparse' / '0', dirs_exist_ok=True)
print("gsplat dataset:", DATA)
```

## 8. Install gsplat and train

The official gsplat project provides a COLMAP capture trainer in `examples/simple_trainer.py`. Its documentation describes the COLMAP dataset layout and training command: https://docs.gsplat.studio/main/examples/colmap.html.

```bash
!git clone https://github.com/nerfstudio-project/gsplat.git /content/gsplat
!pip install -e /content/gsplat
```

Run a short initial training attempt first. The command below is a smoke-test configuration, not a promise of final visual quality:

```bash
!python /content/gsplat/examples/simple_trainer.py default \
  --data_dir /content/tu_dataset \
  --data_factor 2 \
  --result_dir /content/tu_results \
  --max_steps 7000 \
  --save_ply True \
  --ply_steps '[7000]' \
  --disable_viewer True
```

The trainer and CUDA extensions are version-sensitive. If installation or training fails, preserve the full error output and the Colab GPU/PyTorch version before changing package versions. A T4 may run out of memory or be reclaimed before training finishes. Do not assume a run succeeded until the output files exist and are non-empty.

## 9. Convert the trained PLY to SPZ

The Travel Universe viewer expects an SPZ scene. Niantic's open-source SPZ project provides Python bindings and documents PLY-to-SPZ conversion: https://github.com/nianticlabs/spz.

Install the converter:

```bash
!git clone https://github.com/nianticlabs/spz.git /content/spz
!pip install /content/spz
```

Locate the PLY emitted by the trainer and convert it. Because trainer output naming can change between gsplat versions, inspect the output folder before selecting the PLY:

```python
ply_files = sorted(Path('/content/tu_results/ply').glob('*.ply'))
print("PLY files:", ply_files)
assert ply_files, "Training did not produce a PLY file"
```

```python
import spz
ply_path = ply_files[-1]
spz_path = ROOT / 'scene.spz'
unpack_options = spz.UnpackOptions()
unpack_options.to_coord = spz.CoordinateSystem.RUB
cloud = spz.load_splat_from_ply(str(ply_path), unpack_options)
assert cloud.num_points > 0, "PLY contains no Gaussian points"
pack_options = spz.PackOptions()
pack_options.from_coord = spz.CoordinateSystem.RUB
spz.save_spz(cloud, pack_options, str(spz_path))
assert spz_path.is_file() and spz_path.stat().st_size > 0
print("SPZ created:", spz_path, "bytes:", spz_path.stat().st_size,
      "points:", cloud.num_points)
```

If the installed SPZ Python binding has a different API, follow its current Python README: https://github.com/nianticlabs/spz/tree/main/src/python. Do not rename a PLY file to `.spz`; it must be converted.

## 10. Save results and validate

Keep the final SPZ and any useful checkpoint files in Drive. Download a copy to the iPad if you want to inspect it locally. The Niantic SPZ converter can inspect PLY/SPZ files in the browser: https://www.nianticspatial.com/spz-converter.

The completion checks are:

- COLMAP produced non-empty `cameras.bin`, `images.bin`, and `points3D.bin`.
- gsplat training completed and produced a non-empty PLY.
- SPZ conversion produced a non-empty `scene.spz`.
- The SPZ opens in the Travel Universe viewer and renders a coherent scene from the original video.

Only after all checks pass may the app or job API say `world_ready`.

## 11. How this connects to the app today

This Colab process is **manually started from the iPad**. It does not automatically receive jobs from the public Travel Universe website. Colab runtimes are temporary interactive notebooks, not a permanent authenticated API or worker endpoint. The current API/Celery flow expects an S3-compatible object store and a persistent worker; GitHub Pages is static hosting only.

For the first milestone, manually run the notebook, save `scene.spz` in Drive, and verify it in the viewer. A later integration step can add a secure upload/publish handoff between the app and a durable asset location. Do not expose a public Drive link to private videos, put a Google access token in GitHub, or commit generated assets to this public repository.

## Troubleshooting

- **No GPU / no T4 option:** free Colab availability is dynamic. Retry later; CPU can prepare frames, but the CUDA gsplat training cell requires a GPU.
- **Runtime disconnected:** reconnect, remount Drive, and resume from saved Drive files. Do not assume files under `/content` survived.
- **COLMAP fails:** check the frame directory, video motion/blur, and COLMAP error output. A selfie clip with little background parallax may not register every frame.
- **gsplat CUDA install fails:** capture Python, PyTorch, CUDA and GPU versions. Do not randomly upgrade the runtime's preinstalled PyTorch.
- **No PLY output:** training did not complete or PLY export was not enabled; do not attempt SPZ conversion.
- **Viewer rejects SPZ:** verify the SPZ version and the viewer's supported format version. New SPZ v4 files require a reader that supports v4.

## References

- Google Colab FAQ and resource limits: https://research.google.com/colaboratory/faq.html
- COLMAP installation: https://colmap.github.io/install.html
- gsplat COLMAP capture example: https://docs.gsplat.studio/main/examples/colmap.html
- gsplat trainer source: https://github.com/nerfstudio-project/gsplat/blob/main/examples/simple_trainer.py
- SPZ Python bindings: https://github.com/nianticlabs/spz/tree/main/src/python
