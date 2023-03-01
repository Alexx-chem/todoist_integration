import time
import schedule
from typing import Callable

from src import threaded
from src.logger import get_logger
import config

logger = get_logger(__name__, 'console', logging_level=config.GLOBAL_LOG_LEVEL)


class JobManager:

    def __init__(self):
        self.schedule = schedule

    def set_daly_schedule(self, jobs):

        for job in jobs:
            job_period = job.get('period', 1)
            job_time = job.get('time')
            job_func = job.get('func')
            assert isinstance(job_func, Callable), "Job func must be callable!"
            assert job_time, "Job time must be set!"
            self.schedule.every(job_period).day.at(job_time).do(job_func)

    def process_schedule(self):
        while True:
            self.schedule.run_pending()
            time.sleep(30)

    @threaded
    def get_task_state(self):
        logger.info(self.schedule.jobs)
        self.process_schedule()
