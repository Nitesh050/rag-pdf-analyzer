FROM python:3.14-slim
WORKDIR /app

# OpenCV (pulled in by Docling) needs these shared libraries at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# CPU-only PyTorch first: the default Linux wheel pulls ~4GB of CUDA libraries
# that a container on a Mac can't use. requirements.txt then reuses it.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Paths in the app (uploads/, data/chroma_db, data/summaries) are relative
# to /app, so mount volumes there rather than baking data into the image.
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
