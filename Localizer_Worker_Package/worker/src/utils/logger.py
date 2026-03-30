import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """Creates a unified logger configured for the worker node."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

def handle_cuda_oom(e: Exception):
    """
    Special error handler for CUDA OutOfMemoryError.
    """
    error_msg = str(e)
    if "CUDA out of memory" in error_msg or "OutOfMemoryError" in getattr(type(e), '__name__', ''):
        logger = logging.getLogger(__name__)
        logger.critical(f"FATAL: CUDA Out of Memory Error! Aborting current inference: {error_msg}")
        return True
    return False
