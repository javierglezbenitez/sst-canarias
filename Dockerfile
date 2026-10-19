FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/src SST_DATA_DIR=/data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 8000
# La API sirve los resúmenes que haya en /data/processed (monta un volumen con -v).
CMD ["uvicorn", "sstcanarias.api:app", "--host", "0.0.0.0", "--port", "8000"]
