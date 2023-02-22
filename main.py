from time import sleep

import config
from src.todoist import Pipeline
from src import JobManager

from db_worker import DBWorker


DBWorker.set_config(config.DB_CONFIG)


if __name__ == '__main__':
    job_manager = JobManager()

    pipeline = Pipeline()

    # Time in local timezone, in which the service is working!

    # In order to let sync happen before plans refresh
    refresh_delay = config.TODOIST_SYNC_TIMEOUT // 60 + 1
    job_manager.set_daly_schedule([{'time': f"00:{refresh_delay}",
                                    'func': pipeline.refresh_plans}])

    job_manager.get_task_state()

    pipeline.init_db()
    pipeline.load_all_items()
    pipeline.refresh_plans()
    pipeline.update_by_events()

    while True:
        sleep(config.TODOIST_SYNC_TIMEOUT)
        try:
            pipeline.update_by_events()
        except Exception as e:
            print(e)
