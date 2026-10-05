FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY exactjson.py legacy.py stage3.py domain.py server.py ./
COPY web/ ./web/
USER 65534:65534
EXPOSE 8080
CMD ["python", "server.py"]
