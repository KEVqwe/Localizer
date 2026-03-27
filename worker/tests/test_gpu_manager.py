import pytest
from unittest.mock import patch, MagicMock
from worker.src.utils.gpu_manager import free_vram

@patch('worker.src.utils.gpu_manager.gc')
def test_free_vram_calls_gc(mock_gc):
    free_vram()
    mock_gc.collect.assert_called_once()

@patch('worker.src.utils.gpu_manager.torch')
def test_free_vram_calls_cuda_empty_cache(mock_torch):
    mock_torch.cuda.is_available.return_value = True
    free_vram()
    mock_torch.cuda.empty_cache.assert_called()
