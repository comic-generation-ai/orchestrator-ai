FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ proto/
COPY scripts/ scripts/
COPY src/ src/

RUN bash scripts/generate_proto.sh

ARG GRPC_PORT=50052
ENV ORCHESTRATOR_GRPC_PORT=${GRPC_PORT}
EXPOSE ${GRPC_PORT}

CMD ["python", "src/server.py"]
