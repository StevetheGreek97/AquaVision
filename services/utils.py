import re

def extract_logging_path(log_text: str) -> str | None:
    match = re.search(r"Logging results to (.+)", log_text)
    if match:
        raw_path = match.group(1).strip()
        clean_path = re.sub(r'\x1b\[[0-9;]*m', '', raw_path)  # Remove ANSI escape codes
        return clean_path
    return None
