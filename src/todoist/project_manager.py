from src.functions import convert_dt, cut_string
from src.logger import get_logger

import config


logger = get_logger(__name__, 'console', logging_level=config.GLOBAL_LOG_LEVEL)


class GTDHandler:
    def __init__(self, tasks_manager, projects_manager):
        self.tasks_manager = tasks_manager
        self.projects_manager = projects_manager

    def handle_projects(self):

        res = {}

        for project_id, project in self.projects_manager.synced.items():
            res[project_id] = self.parse_project(project, root_project=project.parent_id is None)

        return res

    def parse_project(self, project, root_project=False):
        project_goals = self.get_project_goals(project.id)

        earliest_subtasks = {}
        latest_subtasks = {}
        res_list = []
        active_goals = False

        project_res = {
            'name': project.name,
            'color': project.color,
            'start_date': None,
            'end_date': None,
            'goals': {},
            'warnings': []
        }

        for goal in project_goals.values():
            goal_res = self.parse_goal(goal)

            if goal_res is None:
                continue

            active_goals = True

            res_list.append(goal_res)
            earliest = goal_res[goal.id].get('earliest')
            latest = goal_res[goal.id].get('latest')

            if earliest:
                earliest_subtasks[earliest.id] = earliest

            if latest:
                latest_subtasks[latest.id] = latest

            project_res['goals'].update(goal_res)

        project_earliest = self.tasks_manager.get_extreme_due_task(earliest_subtasks) if earliest_subtasks else None
        project_latest = self.tasks_manager.get_extreme_due_task(latest_subtasks) if latest_subtasks else None

        if not root_project and project_latest and project_earliest:
            project_res['start_date'] = convert_dt(project_earliest.due.date, 'date')
            project_res['end_date'] = convert_dt(project_latest.due.date, 'date')

        if not root_project and project_latest is None and project_earliest is None:
            project_res['warnings'].append(self._handle_project_warn(project, 'Project with no planned duration'))

        if not (active_goals or root_project):
            project_res['warnings'].append(self._handle_project_warn(project, 'Project with no active goals'))

        return project_res

    def parse_goal(self, goal):

        goal_res = None

        if goal.is_active_goal:
            goal_res = {goal.id: dict.fromkeys(('earliest', 'latest', 'start_date', 'end_date', 'success')),
                        'warnings': [],
                        'content': goal.content}

            subtasks = self._get_subtasks(goal.id)
            if not subtasks:
                goal_res['warnings'].append(self._handle_goal_warn(goal, 'Goal without subtasks'))

            else:
                earliest_task = self.tasks_manager.get_extreme_due_task(subtasks, latest=False)
                latest_task = self.tasks_manager.get_extreme_due_task(subtasks, latest=True)
                if None not in (earliest_task, latest_task):
                    goal_res[goal.id]['earliest'] = earliest_task
                    goal_res[goal.id]['latest'] = latest_task
                    goal_res[goal.id]['start_date'] = convert_dt(earliest_task.due.date, 'date')
                    goal_res[goal.id]['end_date'] = convert_dt(latest_task.due.date, 'date')

                if latest_task is not None:
                    if goal.due is None:
                        goal_res['warnings'].append(self._handle_goal_warn(goal, "Goal doesn't have due, steps have"))
                    elif latest_task.due.date != goal.due.date:
                        goal_res['warnings'].append(self._handle_goal_warn(goal, 'Goal due is not equal '
                                                                                 'to the last step due'))

                    # Inefficient. Iterating over subtasks twice
                    success_subtasks = {sub_id: sub for sub_id, sub in subtasks.items()
                                        if config.SPECIAL_LABELS['SUCCESS'] in sub.labels}

                    if success_subtasks:
                        goal_res[goal.id]['success'] = success_subtasks
                        latest_success = self.tasks_manager.get_extreme_due_task(success_subtasks, latest=True)

                        if latest_success and latest_success.due.date != latest_task.due.date:
                            goal_res['warnings'].append(self._handle_goal_warn(goal, '"Success" step is not the last'))
        return goal_res

    def _get_subtasks(self, task_id: str):
        return {sub_id: subtask
                for sub_id, subtask in self.tasks_manager.synced.items()
                if subtask.parent_id == task_id}

    def get_project_goals(self, project_id):
        return {task_id: task
                for task_id, task in self.tasks_manager.synced.items()
                if task.project_id == project_id and config.SPECIAL_LABELS['GOAL'] in task.labels}

    @staticmethod
    def _handle_goal_warn(goal, msg):
        logger.warning(f'{goal.id}: {cut_string(goal.content)}. {msg}')
        return f'<a href="{goal.url}">{goal.content}</a>. {msg}'

    @staticmethod
    def _handle_project_warn(project, msg):
        logger.warning(f'{project.id}: {cut_string(project.name)}. {msg}')
        return f'<a href="{project.url}">{project.name}</a>. {msg}'
