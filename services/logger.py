import logging
import os
import psutil  # For memory usage monitoring

# Create a logger
logger = logging.getLogger('log')
logger.setLevel(logging.DEBUG)

# Console-only handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add only the console handler
logger.addHandler(console_handler)

# Optional: Suppress noisy libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Function to log memory usage
def log_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logger.info(f"Memory Usage: {memory_info.rss / (1024 ** 2):.2f} MB")  # RSS in MB

__all__ = ["logger", "log_memory_usage"]
