# Use official Python runtime as a parent image
ARG PYTHON_BASE_IMAGE=python:3.11-slim
FROM ${PYTHON_BASE_IMAGE}
ARG TARGETARCH

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

# Set work directory
WORKDIR /app

# Install system dependencies
# ffmpeg is required for video processing
# libgl1/libglib2.0 are often needed for cv2 (even headless sometimes depends on them)
# Update sources and install base dependencies
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

RUN pip install --no-cache-dir --retries 10 --timeout 300 -r requirements.txt && \
    pip uninstall -y opencv-python || true && \
    pip install --no-cache-dir --force-reinstall opencv-python-headless

# Copy project files
COPY . .

ENV MYSQL_HOST=127.0.0.1
ENV MYSQL_PORT=3306
ENV MYSQL_USER=root
ENV MYSQL_PASSWORD=123456
ENV MYSQL_DATABASE=geniview

RUN chmod +x /app/docker/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Run the server
CMD ["/app/docker/docker-entrypoint.sh"]
