# Quickstart: Auto Video Localizer

## Overview
This tool takes a standard 1-minute English video and generates 9 fully localized versions (DE, ES, FR, ID, IT, PL, PT, RU, TR) simultaneously. It processes audio extraction, transcription, translation, dubbing, and subtitle/UI burning.

## Setup
1. Clone the repository.
2. Ensure you have Python 3.11 installed.
3. Install system dependencies (requires FFmpeg):
   ```bash
   sudo apt-get install ffmpeg  # or brew install ffmpeg / choco install ffmpeg
   ```
4. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Configure your environment variables for the LLM translation API and local TTS models in `.env`.

## Running the Server
Start the backend API and frontend service:
```bash
uvicorn src.main:app --reload
```

## Usage (API)
Send a video to be localized:
```bash
curl -X POST -F "video_file=@sample_1min.mp4" http://localhost:8000/api/v1/jobs
```
Receive the `job_id` and poll `/api/v1/jobs/{job_id}` until completion. The response will contain direct download links for the 9 generated videos.
