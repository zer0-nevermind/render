FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy pillow
COPY render.py .
ENTRYPOINT ["python", "render.py"]
