import logging
import os
import psutil  # For memory usage monitoring

# Create a logger
logger = logging.getLogger('log')
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('app.log')

# Set log levels
console_handler.setLevel(logging.DEBUG)
file_handler.setLevel(logging.INFO)

# Create a formatter and set it for the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Function to log memory usage
def log_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logger.info(f"Memory Usage: {memory_info.rss / (1024 ** 2):.2f} MB")  # RSS in MB

# Optional: Suppress duplicate loggers in libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Export the logger
__all__ = ["logger", "log_memory_usage"]

# Function to log memory usage
def log_memory_usage():
    # Get the current process's memory usage
    process = psutil.Process()  # This gets the current process
    memory_info = process.memory_info()  # This gives memory info (in bytes)

