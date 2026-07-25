FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY security/ ./security/
COPY pipeline/ ./pipeline/
COPY training/ ./training/
COPY serving/ ./serving/
COPY dashboard/ ./dashboard/

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
