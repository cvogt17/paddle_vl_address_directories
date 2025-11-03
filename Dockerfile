FROM ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server_api.py .

ENV PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PORT=8080

EXPOSE 8080

CMD ["uvicorn", "server_api:app", "--host", "0.0.0.0", "--port", "8080"]
