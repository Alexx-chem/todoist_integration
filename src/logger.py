import logging
import os


log_levels = {'error': logging.ERROR,
              'warning': logging.WARNING,
              'info': logging.INFO,
              'debug': logging.DEBUG}


def get_logger(logger_name, logger_type, logging_level='info',  **kwargs):

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger(logger_name)

    logger.setLevel(log_levels[logging_level.lower()])

    if logger_type == 'console':
        handler = logging.StreamHandler()
    elif logger_type == 'file':
        log_file_dir = kwargs.get('log_file_dir', "")
        log_file_name = kwargs.get('log_file_name')

        assert log_file_name is not None, "Log file name is None!"

        log_file_full_path = os.path.join(log_file_dir, log_file_name)

        handler = logging.FileHandler(log_file_full_path)
    else:
        raise ValueError(f"Unrecognized logger_type: {logger_type}")

    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger
