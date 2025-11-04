# 1. Start from a RunPod base image with CUDA 12.1
# This provides the necessary NVIDIA drivers and a base Python environment.
# Source: [25, 27]
FROM runpod/base:0.6.2-cuda12.1.0

# 2. Set environment variables to non-interactive to prevent apt from hanging
ENV DEBIAN_FRONTEND=noninteractive

# 3. Install system-level dependencies for OpenCV (required by paddleocr)
# Failure to do this will cause an 'ImportError: libGL.so.1'
# Sources: [29, 30, 31, 33]
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev && \
    rm -rf /var/lib/apt/lists/*

# 4. Set up the working directory
WORKDIR /app

# 5. Copy the Python requirements file
COPY requirements.txt.

# 6. Install all Python dependencies from requirements.txt
# This installs runpod, paddlepaddle-gpu, and paddleocr[doc-parser]
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy the handler script into the image
COPY rp_handler.py.

# 8. Define the container's entrypoint
# This command starts the RunPod worker, which waits for jobs
# Sources: [13, 22]
CMD ["python", "-u", "rp_handler.py"]
