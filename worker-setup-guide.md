# Worker Node Setup Guide

Follow this strictly to deploy a Worker Node on another studio workstation over Gigabit LAN.

## Requirements
- RTX 4070 or 4080 (12GB+ VRAM required)
- Python 3.11 installed
- FFmpeg installed in PATH

## Steps
1. Clone the `Localizer` repo onto the target node.
2. `cd worker` and `pip install -r requirements.txt`
3. Identify the Server's IP address (e.g., `192.168.1.100`)
4. Create `.env` file in the root:
   ```env
   CELERY_BROKER_URL=redis://:YOUR_REDIS_PASSWORD@192.168.1.100:6379/0
   OPENAI_API_KEY=your_key
   ELEVENLABS_API_KEY=your_key
   ```
5. Run the node daemon and celery thread:
   ```bash
   # Terminal 1: GPU monitor
   python -m worker.src.monitor
   
   # Terminal 2: Celery Worker
   celery -A worker.src.celery_tasks worker --loglevel=info --concurrency=1
   ```
   *(Concurrency must be 1 to preserve 12GB VRAM per machine)*
