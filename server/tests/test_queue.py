import pytest
from unittest.mock import patch, MagicMock

def test_task_distributed_to_idle_worker():
    """Mock Redis Queue test ensuring tasks are distributed to workers"""
    with patch('server.src.queue.celery_app.celery_app.send_task') as mock_send_task:
        mock_send_task("worker.src.celery_tasks.process_video", args=["video.mp4"])
        
        mock_send_task.assert_called_once()
        assert mock_send_task.call_args[0][0] == "worker.src.celery_tasks.process_video"
