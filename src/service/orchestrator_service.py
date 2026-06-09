import logging

import grpc

from src.generated import orchestrator_pb2, orchestrator_pb2_grpc
from src.workflow.comic_job import ComicJobWorkflow

logger = logging.getLogger(__name__)


class ComicOrchestratorService(orchestrator_pb2_grpc.ComicOrchestratorServiceServicer):
    def __init__(self, workflow: ComicJobWorkflow, image_ai_healthy: bool):
        self._workflow = workflow
        self._image_ai_healthy = image_ai_healthy

    def StartComicGeneration(self, request, context):
        if not (request.summary or "").strip():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("summary không được rỗng")
            return orchestrator_pb2.StartComicGenerationResponse()

        num_panels = request.num_panels if request.num_panels > 0 else 4

        try:
            state = self._workflow.start(
                job_id=request.job_id,
                user_id=request.user_id,
                summary=request.summary,
                style=request.style,
                num_panels=num_panels,
                request_id=request.request_id,
            )
        except ValueError as exc:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(str(exc))
            return orchestrator_pb2.StartComicGenerationResponse()

        logger.info("Started comic job %s", request.job_id)
        return orchestrator_pb2.StartComicGenerationResponse(
            job_id=state.job_id,
            status=state.status,
        )

    def GetComicJobStatus(self, request, context):
        state = self._workflow.get(request.job_id)
        if not state:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"job_id {request.job_id} không tồn tại")
            return orchestrator_pb2.GetComicJobStatusResponse()
        return state.to_status_response()

    def CancelComicJob(self, request, context):
        state = self._workflow.cancel(request.job_id)
        if not state:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"job_id {request.job_id} không tồn tại")
            return orchestrator_pb2.CancelComicJobResponse()

        return orchestrator_pb2.CancelComicJobResponse(
            job_id=state.job_id,
            status=state.status,
        )

    def CheckHealth(self, request, context):
        return orchestrator_pb2.CheckHealthResponse(
            is_alive=True,
            dependencies={"image-ai": "ok" if self._image_ai_healthy else "unreachable"},
        )
