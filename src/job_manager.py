import time
import schedule


class JobManager:

    def __init__(self):
        self.schedule = schedule

    def set_daly_schedule(self, jobs):

        for job in jobs:
            job_period = job.get('period', 1)
            job_time = job.get('time')
            job_func = job.get('func')
            assert job_func, "Job callable must be set!"
            assert job_time, "Job time must be set!"
            self.schedule.every(job_period).day.at(job_time).do(job_func)

    def process_schedule(self):
        while True:
            self.schedule.run_pending()
            time.sleep(30)
