"""Unit tests for comic job cancellation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.generated import orchestrator_pb2
from src.clients.story_client import StoryGenerationCancelledError
from src.workflow.comic_job import ComicJobState, ComicJobWorkflow, PanelScriptData


class _MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, dict] = {}

    def save(self, job_id: str, payload: dict) -> None:
        self._data[job_id] = dict(payload)

    def load(self, job_id: str) -> dict | None:
        stored = self._data.get(job_id)
        return dict(stored) if stored else None


def _queued_state(job_id: str = "job-1") -> ComicJobState:
    return ComicJobState(
        job_id=job_id,
        user_id="user-1",
        summary="test",
        style="comic",
        request_id="req-1",
        num_panels=2,
        progress_total=2,
        status=orchestrator_pb2.COMIC_JOB_QUEUED,
    )


class ComicJobCancelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _MemoryStore()
        self.image_client = MagicMock()
        self.story_client = MagicMock()
        self.workflow = ComicJobWorkflow(self.store, self.image_client, self.story_client)

    def test_cancel_notifies_story_ai_and_revokes_image_tasks(self) -> None:
        state = _queued_state()
        state.image_task_ids = ["task-a", None, "task-b"]
        self.store.save(state.job_id, state.to_dict())

        result = self.workflow.cancel(state.job_id)

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.cancel_requested)
        self.assertEqual(result.status, orchestrator_pb2.COMIC_JOB_CANCELLED)
        self.story_client.cancel_story.assert_called_once_with(state.job_id)
        self.image_client.cancel_task.assert_any_call("task-a")
        self.image_client.cancel_task.assert_any_call("task-b")
        self.assertEqual(self.image_client.cancel_task.call_count, 2)

    def test_pipeline_keeps_cancelled_when_poll_raises(self) -> None:
        state = _queued_state()
        self.store.save(state.job_id, state.to_dict())

        scripts = [
            PanelScriptData(
                index=0,
                caption_vi="hi",
                prompt_en="prompt",
                scene_description="scene",
            )
        ]

        self.story_client.generate_story.return_value = MagicMock(
            panels=scripts,
            characters={},
        )
        self.image_client.submit_panel.return_value = "task-1"

        def poll_and_cancel(*_args, **_kwargs):
            data = self.store.load(state.job_id)
            assert data is not None
            data["cancel_requested"] = True
            data["status"] = orchestrator_pb2.COMIC_JOB_CANCELLED
            self.store.save(state.job_id, data)
            raise RuntimeError("Task task-1 bị huỷ giữa chừng (cancel_requested)")

        self.image_client.poll_task.side_effect = poll_and_cancel

        self.workflow._run_pipeline(state.job_id)

        persisted = self.store.load(state.job_id)
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertTrue(persisted["cancel_requested"])
        self.assertEqual(persisted["status"], orchestrator_pb2.COMIC_JOB_CANCELLED)

    def test_pipeline_story_cancelled_error_keeps_cancelled_status(self) -> None:
        state = _queued_state()
        self.store.save(state.job_id, state.to_dict())
        self.story_client.generate_story.side_effect = StoryGenerationCancelledError("cancelled")

        self.workflow._run_pipeline(state.job_id)

        persisted = self.store.load(state.job_id)
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted["status"], orchestrator_pb2.COMIC_JOB_CANCELLED)


if __name__ == "__main__":
    unittest.main()
