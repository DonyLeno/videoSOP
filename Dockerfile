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
RUN if [ -f /etc/apt/sources.list ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; fi && if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; fi && apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    mariadb-server \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN if [ "${TARGETARCH}" = "amd64" ]; then \
    curl -L --retry 10 --retry-delay 10 --retry-connrefused -o torch-2.2.2+cpu-cp311-cp311-linux_x86_64.whl ${TORCH_WHL_URL} && \
    pip install --no-cache-dir torch-2.2.2+cpu-cp311-cp311-linux_x86_64.whl torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cpu --extra-index-url ${PIP_INDEX_URL} && \
    rm torch-2.2.2+cpu-cp311-cp311-linux_x86_64.whl; \
fi
RUN pip install --no-cache-dir --retries 10 --timeout 300 -r requirements.txt

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
