FROM python:3.9-alpine
WORKDIR /app
COPY app.py .
RUN pip install flask
RUN mkdir /shared_logs 
CMD ["python", "app.py"]
