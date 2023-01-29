from time import sleep

import config
from src.todoist import TodoistApi
from src import JobManager
from src import threaded


@threaded
def get_task_state(td_api):
    JobManager(td_api)


if __name__ == '__main__':

    todoist_api = TodoistApi(config.todoist_token)
    todoist_api.run()

    task_manager = get_task_state(todoist_api)

    while True:
        sleep(15)
        todoist_api.sync_all_objects()
        todoist_api.save_all_objects()
