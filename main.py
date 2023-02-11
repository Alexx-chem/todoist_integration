from time import sleep

import config
from src.todoist import Pipeline
from src import JobManager

from db_worker import DBWorker


DBWorker.set_config(config.DB_CONFIG)


if __name__ == '__main__':
    job_manager = JobManager()

    pipeline = Pipeline()

    # Указывать время в том часовом поясе, в котором код будет работать!
    job_manager.set_daly_schedule([{'time': "00:05",
                                    'func': pipeline.refresh_plans}])

    job_manager.get_task_state()

    while True:
        sleep(config.TODOIST_SYNC_TIMEOUT)
        pipeline.sync_all_items()
