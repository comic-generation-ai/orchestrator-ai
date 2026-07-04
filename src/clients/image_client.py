import logging
import time
from dataclasses import dataclass

import grpc

from src.generated import image_generation_pb2, image_generation_pb2_grpc
from src.config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class ImagePanelResult:
  image_url: str
  seed: int
  task_id: str


class ImageAiClient:
  """gRPC client gọi image-ai GenerateImageAsync + poll GetTaskStatus."""

  def __init__(self, settings: Settings):
    self._settings = settings
    self._channel = grpc.insecure_channel(settings.IMAGE_AI_GRPC_TARGET)
    self._stub = image_generation_pb2_grpc.ImageGenerationServiceStub(self._channel)

  def check_health(self) -> bool:
    try:
      resp = self._stub.CheckHealth(image_generation_pb2.CheckHealthRequest(), timeout=5)
      return resp.is_alive
    except grpc.RpcError as exc:
      logger.warning("image-ai health check failed: %s", exc.details())
      return False

  def generate_panel(
    self,
    *,
    prompt: str,
    caption_vi: str,
    reference_image_url: str = "",
    seed: int = -1,
  ) -> ImagePanelResult:
    request = image_generation_pb2.GenerateImageRequest(
      prompt=prompt,
      width=self._settings.image_width,
      height=self._settings.image_height,
      seed=seed,
      num_inference_steps=self._settings.image_steps,
      caption_text=caption_vi,
      reference_image_url=reference_image_url or "",
    )
    response = self._stub.GenerateImageAsync(request, timeout=30)
    task_id = response.task_id
    logger.info("image-ai task queued: %s", task_id)
    return self._poll_task(task_id)

  def _poll_task(self, task_id: str) -> ImagePanelResult:
    for attempt in range(self._settings.IMAGE_POLL_MAX_ATTEMPTS):
      status_resp = self._stub.GetTaskStatus(
        image_generation_pb2.TaskStatusRequest(task_id=task_id),
        timeout=15,
      )
      status = status_resp.status

      if status == image_generation_pb2.PROCESSING:
        time.sleep(self._settings.image_poll_interval_sec)
        continue

      if status == image_generation_pb2.SUCCESS:
        if not status_resp.minio_url:
          raise RuntimeError(f"Task {task_id} SUCCESS nhưng thiếu minio_url")
        return ImagePanelResult(
          image_url=status_resp.minio_url,
          seed=-1,
          task_id=task_id,
        )

      if status == image_generation_pb2.FAILED:
        raise RuntimeError(status_resp.error_message or f"image-ai task {task_id} FAILED")

      time.sleep(self._settings.image_poll_interval_sec)

    raise TimeoutError(f"image-ai task {task_id} timeout sau {self._settings.image_poll_max_attempts} lần poll")

  def cancel_task(self, task_id: str) -> None:
    try:
      self._stub.CancelTask(image_generation_pb2.CancelRequest(task_id=task_id), timeout=10)
    except grpc.RpcError as exc:
      logger.warning("cancel task %s failed: %s", task_id, exc.details())

  def close(self) -> None:
    self._channel.close()
