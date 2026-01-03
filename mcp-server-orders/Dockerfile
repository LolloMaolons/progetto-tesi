FROM python:3.11-slim
WORKDIR /app
COPY server.py .
RUN pip install --no-cache-dir redis==5.2.0
CMD ["python", "server.py"]