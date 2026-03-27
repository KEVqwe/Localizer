import pytest
from unittest.mock import patch
from worker.src.utils.ffmpeg_manager import run_ffmpeg_command

@patch('worker.src.utils.ffmpeg_manager.subprocess.run')
@patch('worker.src.utils.ffmpeg_manager.shutil.which')
def test_ffmpeg_nvenc_muxing(mock_which, mock_run):
    # Mock ffmpeg executable found
    mock_which.return_value = "/usr/bin/ffmpeg"
    
    # Run a dummy command that should include nvenc
    args = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda", "-i", "input.mp4", "-c:v", "h264_nvenc", "output.mp4"]
    result = run_ffmpeg_command(args)
    
    assert result is True
    # Verify the correct command was passed
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert "h264_nvenc" in called_args
