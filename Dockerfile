FROM registry.access.redhat.com/ubi9/python-311:latest

WORKDIR /app
RUN pip install --no-cache-dir prometheus-api-client requests pyyaml rich
COPY orchestrator.py /app/orchestrator.py
ENTRYPOINT ["python", "/app/orchestrator.py"]

