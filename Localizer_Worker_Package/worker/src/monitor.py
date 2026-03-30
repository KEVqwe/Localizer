import time
import socket
from server.src.models.models import WorkerStatus
from worker.src.utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import torch
except ImportError:
    torch = None

def get_node_status() -> WorkerStatus:
    """
    Checks CUDA utilization to determine if node is IDLE or BUSY.
    """
    if torch is not None and torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / (1024 ** 2)
        if allocated > 1000:
            return WorkerStatus.BUSY
    
    return WorkerStatus.IDLE

def report_status_loop():
    """
    Daemon loop that pings the server with current IDLE/BUSY status.
    """
    hostname = socket.gethostname()
    while True:
        status = get_node_status()
        logger.info(f"Node {hostname} status: {status.value}")
        time.sleep(10)

if __name__ == "__main__":
    report_status_loop()
