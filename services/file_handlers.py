import os
import psutil
def loader(folder_path):
    valid_extensions = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", '.tif')
    if folder_path:
        image_paths = []
        for f in os.listdir(folder_path):
            joined = os.path.join(folder_path, f)
            if joined.endswith(valid_extensions):
                image_paths.append(joined)
        return image_paths
    else:
        return None


# Function to log memory usage
def log_memory_usage():
    # Get the current process's memory usage
    process = psutil.Process()  # This gets the current process
    memory_info = process.memory_info()  # This gives memory info (in bytes)
