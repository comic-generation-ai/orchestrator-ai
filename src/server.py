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
from src.clients.story_client import StoryClient
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

    story_client = StoryClient(settings)
    story_ok = story_client.check_health()
    if not story_ok:
        logger.warning("story-ai không phản hồi health check tại %s — job sẽ FAILED khi tới bước sinh truyện", settings.STORY_AI_API_URL)

    store = ComicJobStore(settings.redis_url, ttl_sec=settings.redis_job_ttl_sec)
    workflow = ComicJobWorkflow(store=store, image_client=image_client, story_client=story_client)
    servicer = ComicOrchestratorService(workflow=workflow, image_ai_healthy=image_ok, story_ai_healthy=story_ok)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    orchestrator_pb2_grpc.add_ComicOrchestratorServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"{settings.grpc_host}:{settings.grpc_port}")
    server.start()

    logger.info(
        "orchestrator-ai gRPC listening on %s:%s (image-ai=%s)",
        settings.grpc_host,
        settings.grpc_port,
        settings.image_ai_grpc_target,
    )
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
