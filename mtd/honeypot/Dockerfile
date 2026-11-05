FROM python:3.11-alpine
WORKDIR /app
RUN pip install --no-cache-dir flask && mkdir -p /shared_logs
COPY app.py .
CMD ["python", "app.py"]
