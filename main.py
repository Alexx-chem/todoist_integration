from time import sleep

import config
from src.todoist import TodoistApi
from src import JobManager


if __name__ == '__main__':
    job_manager = JobManager()

    todoist_api = TodoistApi(config.TODOIST_API_TOKEN)
    todoist_api.run()

    # Указывать время в том часовом поясе, в котором код будет работать!
    job_manager.set_daly_schedule([{'time': "00:05",
                                    'func': todoist_api.refresh_plans}])

    job_manager.get_task_state()

    while True:
        sleep(config.TODOIST_SYNC_TIMEOUT_SECONDS)
        #todoist_api.sync_all_objects()
