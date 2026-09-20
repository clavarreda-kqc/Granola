FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 GRANOLA_DATA_DIR=/data
WORKDIR /srv/granola
COPY app ./app
COPY data ./data
RUN mkdir -p /data/recordings && chown -R 65532:65532 /data
USER 65532:65532
EXPOSE 8080
CMD ["python", "app/server.py"]
