import time
import schedule


class ScheduledJob:

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


class JobManager(ScheduledJob):

    def __init__(self, todoist_api):
        super().__init__()

        # Указывать время в том часовом поясе, в котором код будет работать!
        self.set_daly_schedule([
            {'time': "07:00",
             'func': todoist_api.daily_report},
            {'time': "05:00",
             'func': todoist_api.planner.refresh_plans()},
        ])

        print(self.schedule.jobs)
        self.process_schedule()
