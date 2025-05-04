import logging
import os

def setup_logging(
    log_filename="analysis.log",
    log_dir="./logs",
    console_level=logging.INFO,
    file_level=logging.DEBUG
):
    """
    Sets up the logging system with separate levels for console and log file output.

    Args:
        log_filename (str): Name of the log file.
        log_dir (str): Directory where the log file will be saved.
        console_level (int): Minimum log level for console output (e.g., logging.INFO).
        file_level (int): Minimum log level for file output (e.g., logging.DEBUG).
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Capture everything, filter per handler

    # Clear any existing handlers (important in Jupyter or repeated runs)
    logger.handlers.clear()

    # File handler (writes full debug log to file)
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))
    logger.addHandler(file_handler)

    # Console handler (more selective)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    logger.addHandler(console_handler)

    logging.info("Logging initialized. File: %s", log_path)
