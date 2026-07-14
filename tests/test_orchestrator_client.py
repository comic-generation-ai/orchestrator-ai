"""Test orchestrator gRPC — chạy khi image-ai + celery + redis đang hoạt động."""

import sys
import time
import uuid
from pathlib import Path

import grpc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.generated import orchestrator_pb2, orchestrator_pb2_grpc


def main() -> None:
    target = "localhost:50054"
    channel = grpc.insecure_channel(target)
    stub = orchestrator_pb2_grpc.ComicOrchestratorServiceStub(channel)

    health = stub.CheckHealth(orchestrator_pb2.CheckHealthRequest())
    print("Health:", dict(health.dependencies), "alive=", health.is_alive)

    job_id = str(uuid.uuid4())
    summary = """Ngày xửa ngày xưa, ở một làng quê nghèo nọ, có hai chị em Tấm và Cám cùng chung sống với mẹ kế. 
    Tấm là cô gái hiền lành, xinh đẹp và đảm đang, còn Cám lại là một cô gái lười biếng, đanh đá và gian ác. 
    Mẹ con Cám luôn tìm cách hãm hại Tấm, bắt cô làm đủ mọi việc nặng nhọc và không cho cô được hưởng hạnh phúc. 
    Một hôm, nhà vua mở hội thi kén rể, Tấm cũng muốn đi dự nhưng bị mẹ con Cám ngăn cản. 
    Tấm rất buồn và thất vọng, nhưng bà Bụt đã hiện lên và giúp đỡ cô bằng cách biến những vật quen thuộc xung quanh Tấm thành những vật phẩm lộng lẫy để cô có thể đi dự hội. 
    """

    start = stub.StartComicGeneration(
        orchestrator_pb2.StartComicGenerationRequest(
            job_id=job_id,
            user_id="dev-user",
            summary=summary,
            style="children",
            num_panels=4,
            request_id=str(uuid.uuid4()),
        )
    )
    print(f"Started job {start.job_id}, status={start.status}")

    for i in range(600):
        status = stub.GetComicJobStatus(
            orchestrator_pb2.GetComicJobStatusRequest(job_id=job_id)
        )
        print(
            f"[{i * 2}s] {status.current_step} | "
            f"progress={status.progress_current}/{status.progress_total} | "
            f"status={status.status}"
        )
        if status.status in (
            orchestrator_pb2.COMIC_JOB_SUCCESS,
            orchestrator_pb2.COMIC_JOB_FAILED,
            orchestrator_pb2.COMIC_JOB_CANCELLED,
        ):
            if status.status == orchestrator_pb2.COMIC_JOB_SUCCESS:
                for panel in status.panels:
                    print(f"  Panel {panel.index}: {panel.image_url}")
            else:
                print("Error:", status.error_message)
            break
        time.sleep(2)
    else:
        print("Timeout waiting for job")


if __name__ == "__main__":
    main()
