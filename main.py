from time import sleep

import config
from src.todoist import TodoistApi
from src import JobManager
from src import threaded


@threaded
def get_task_state(td_api):
    job_manager = JobManager()

    # Указывать время в том часовом поясе, в котором код будет работать!
    job_manager.set_daly_schedule(
        [
            {'time': "07:00",
             'func': td_api.daily_report},
            {'time': "05:00",
             'func': td_api.planner.refresh_plans()}
        ]
    )

    print(job_manager.schedule.jobs)
    job_manager.process_schedule()


if __name__ == '__main__':

    todoist_api = TodoistApi(config.TODOIST_TOKEN)
    todoist_api.run()

    task_manager = get_task_state(todoist_api)

    while True:
        sleep(15)
        todoist_api.sync_all_objects()
        todoist_api.save_all_objects()
