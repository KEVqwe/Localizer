import gc
import logging
import os

# Reduce VRAM fragmentation
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

try:
    import torch
except ImportError:
    torch = None

logger = logging.getLogger(__name__)

def free_vram():
    """
    Strict CUDA cleaner hook to forcefully free VRAM between AI models 
    to prevent OOM errors on GPUs with limited VRAM (e.g. RTX 4070 12GB).
    """
    if torch is not None and torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
    
    # Force garbage collection
    gc.collect()
    
    if torch is not None and torch.cuda.is_available():
        logger.info(f"VRAM Freed. Current allocated: {torch.cuda.memory_allocated() / (1024 ** 2):.2f} MB")
