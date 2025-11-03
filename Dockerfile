# Use the base image that already includes PaddleOCR-VL and dependencies
FROM ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest

WORKDIR /app

# Copy and install your light dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your handler script
COPY server_api.py .

# Use handler (SDK) mode instead of HTTP server
CMD ["python", "server_api.py"]
