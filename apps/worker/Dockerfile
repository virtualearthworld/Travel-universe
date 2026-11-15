FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY apps/worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/worker/app.py ./app.py
COPY apps/worker/colmap_pipeline.py ./colmap_pipeline.py
CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=INFO"]
