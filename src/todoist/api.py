from todoist_api_python.api import TodoistAPI as Rest_API
from todoist.api import TodoistAPI as Sync_API
from collections import defaultdict
from typing import Callable

from src.logger import get_logger
import config


logger = get_logger(__name__, 'console', config.GLOBAL_LOG_LEVEL)


class TodoistApi:
    def __init__(self, api_token):
        logger.debug("TodoistApi init")
        self.rest_api = Rest_API(api_token)
        self.sync_api = Sync_API(api_token, api_version=config.TODOIST_API_VERSION)
        self.token = api_token

    @staticmethod
    def _tasks_by_project_to_string(tasks_by_projects_list, header: str):
        out = f'<b>{header}</b>\n\n'
        for project_name in tasks_by_projects_list:
            out += f'\U0001F4CB {project_name}\n'
            for goal in tasks_by_projects_list[project_name]:
                out += f'    \U0001f539 <a href="{goal.url}">{goal.content}</a>\n'
            out += '\n'
        return out

    def _get_goals_with_subtasks(self):
        goals = [self.tasks[task] for task in self.tasks if config.GOAL_LABEL_NAME in self.tasks[task].labels]
        return tuple(zip(goals, [self._get_subtasks(goal) for goal in goals]))

    def _check_success_label(self, tasks):
        return self._check_label_among_tasks(tasks, config.SUCCESS_LABEL_NAME)

    @staticmethod
    def _check_label_among_tasks(tasks, label):
        return [label in task.labels for task in tasks]

    def _filter_goals(self, subtasks_filter: Callable):
        out = defaultdict(list)
        for goal, subtasks in self._get_goals_with_subtasks():

            filtered_subs = any(subtasks_filter(subtasks))

            if not filtered_subs and goal.priority in (3, 4):
                project = self.projects[goal.project_id]
                out[project.name].append(goal)

        return out
