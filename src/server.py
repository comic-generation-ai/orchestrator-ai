import logging
import sys
from concurrent import futures
from pathlib import Path

import grpc

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import get_settings
from src.clients.image_client import ImageAiClient
from src.state.redis_store import ComicJobStore
from src.workflow.comic_job import ComicJobWorkflow
from src.service.orchestrator_service import ComicOrchestratorService
from src.generated import orchestrator_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def serve() -> None:
    settings = get_settings()
    image_client = ImageAiClient(settings)
    image_ok = image_client.check_health()

    store = ComicJobStore(settings.REDIS_URL, ttl_sec=settings.REDIS_JOB_TTL_SEC)
    workflow = ComicJobWorkflow(store=store, image_client=image_client)
    servicer = ComicOrchestratorService(workflow=workflow, image_ai_healthy=image_ok)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    orchestrator_pb2_grpc.add_ComicOrchestratorServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"{settings.GRPC_HOST}:{settings.GRPC_PORT}")
    server.start()

    logger.info(
        "orchestrator-ai gRPC listening on %s:%s (image-ai=%s)",
        settings.GRPC_HOST,
        settings.GRPC_PORT,
        settings.IMAGE_AI_GRPC_TARGET,
    )
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
