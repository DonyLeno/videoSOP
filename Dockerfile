# Use official Python runtime as a parent image
ARG PYTHON_BASE_IMAGE=python:3.11-slim
FROM ${PYTHON_BASE_IMAGE}
ARG TARGETARCH

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ARG TORCH_WHL_URL=https://download.pytorch.org/whl/cpu/torch-2.2.2%2Bcpu-cp311-cp311-linux_x86_64.whl

# Set work directory
WORKDIR /app

# Install system dependencies
# ffmpeg is required for video processing
# libgl1/libglib2.0 are often needed for cv2 (even headless sometimes depends on them)
# Update sources and install base dependencies
# Removed libsm6, libxext6, libxrender1 as they are X11/GUI libraries not needed for headless
RUN if [ -f /etc/apt/sources.list ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; fi && \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; fi

# Split installs to prevent OOM
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install ffmpeg separately
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install mariadb-server separately
RUN apt-get update && apt-get install -y --no-install-recommends \
    mariadb-server \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

# CRITICAL: Install CPU-only versions of torch AND torchvision BEFORE requirements.txt
# If we don't install torchvision here, pip install ultralytics will pull the default (CUDA) torchvision,
# which will then pull the default (CUDA) torch, causing massive image size.
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "amd64" ]; then \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    else \
    pip install --no-cache-dir torch torchvision; \
    fi

RUN pip install --no-cache-dir --retries 10 --timeout 300 -r requirements.txt && \
    pip uninstall -y opencv-python || true && \
    pip install --no-cache-dir --force-reinstall opencv-python-headless && \
    yolo settings updates=false sync=false

# Copy project files
COPY . .

ENV MYSQL_HOST=127.0.0.1
ENV MYSQL_PORT=3306
ENV MYSQL_USER=root
ENV MYSQL_PASSWORD=123456
ENV MYSQL_DATABASE=geniview

RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Run the server
CMD ["/app/docker-entrypoint.sh"]
