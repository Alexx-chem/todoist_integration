import logging
import sys
import os


def get_logger(logger_name, logger_type, logging_level,  **kwargs):
    # Create a custom logger
    logger = logging.getLogger(logger_name)

    # Create handlers
    if logger_type == 'console':
        handler = logging.StreamHandler(sys.stdout)

    elif logger_type == 'file':
        log_file_dir = kwargs.get('log_file_dir', "")
        log_file_name = kwargs.get('log_file_name')

        assert log_file_name is not None, "Log file name is None!"

        log_file_full_path = os.path.join(log_file_dir, log_file_name)

        handler = logging.FileHandler(log_file_full_path)
    else:
        raise ValueError(f"Unrecognized logger_type: {logger_type}")

    handler.setLevel(logging_level)

    # Create formatters and add it to handlers
    logger_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(logger_format)

    # Add handlers to the logger
    logger.addHandler(handler)

    return logger
