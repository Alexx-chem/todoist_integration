import joblib
import json
import os
from todoist_api_python.api import TodoistAPI as Rest_API, Task
from todoist.api import TodoistAPI as Sync_API
from collections import defaultdict
from typing import Callable, Iterable, List
import requests

import config

from src.todoist.extended_task import ExtendedTask
from src.todoist.planner import Planner
from src.functions import set_db_timezone


class TodoistApi:
    def __init__(self, todoist_api_token):
        self.rest_api = Rest_API(todoist_api_token)
        self.sync_api = Sync_API(todoist_api_token, api_version=config.TODOIST_API_VERSION)
        self.token = todoist_api_token

        self.tasks = None
        self.projects = None
        self.labels = None
        self.done_tasks = None
        self.task_activity = None

        self.goals_with_subtasks = None

        self.planner = Planner()

        set_db_timezone()

    def run(self):
        try:
            self.load_all_objects()
            process_diff = True
        except (FileNotFoundError, Exception) as e:
            print(e)
            process_diff = False

        self.sync_all_objects(process_diff, feed_planner=True)
        self.save_all_objects()

    def save_all_objects(self):
        scope = {'tasks': self.tasks,
                 'projects': self.projects,
                 'labels': self.labels,
                 'done_tasks': self.done_tasks,
                 'task_activity': self.task_activity}
        joblib.dump(scope, 'todoist_scope')

    def load_all_objects(self):
        scope = joblib.load('todoist_scope')
        self.__dict__.update(scope)

    def sync_all_objects(self, process_diff=True, feed_planner=False):

        tasks = self._sync_todo_tasks()
        projects = self._sync_projects()
        labels = self._sync_labels()
        done_tasks = self._sync_done_tasks(projects)
        task_activity = self._sync_activity()

        scope = {
            'tasks': tasks,
            'projects': projects,
            'labels': labels,
            'done_tasks': done_tasks,
            'task_activity': task_activity
        }

        if feed_planner:
            # TODO Dirty hack...
            self.planner.run(tasks)

        if process_diff:
            self._process_scope_diff(scope)

        self.__dict__.update(scope)

        self.goals_with_subtasks = self._get_goals_with_subtasks()

    def _process_scope_diff(self, scope):

        task_to_action_map = []

        out_of_scope_tasks = self.tasks.keys() - scope['tasks'].keys()
        print('out_of_scope_tasks', out_of_scope_tasks)

        new_tasks = scope['tasks'].keys() - self.tasks.keys() - self.done_tasks.keys()
        print('new_tasks', new_tasks)
        task_to_action_map.extend([(task_id, 'created') for task_id in new_tasks])

        common_tasks = scope['tasks'].keys() & self.tasks.keys()
        undone_tasks = scope['tasks'].keys() & self.done_tasks.keys()
        modified_tasks = self._get_tasks_diff(scope, common_tasks)
        modified_done_tasks = self._get_tasks_diff(scope, undone_tasks)
        print('modified_tasks', modified_tasks | modified_done_tasks)

        task_to_action_map.extend([(task_id, 'modified') for task_id in modified_tasks])

        completed_tasks = out_of_scope_tasks & scope['done_tasks'].keys()
        print('completed_tasks', completed_tasks)
        task_to_action_map.extend([(task_id, 'completed') for task_id in completed_tasks])

        deleted_tasks = out_of_scope_tasks - completed_tasks
        print('deleted_tasks', deleted_tasks)
        task_to_action_map.extend([(task_id, 'deleted') for task_id in deleted_tasks])

        for task_id, action in task_to_action_map:

            if action == "completed":
                task = scope['done_tasks'][task_id]
            elif action == "deleted":
                task = self.tasks[task_id]
            else:
                task = scope['tasks'][task_id]

            self.planner.process_task(task, action)

    def _process_modified_tasks(self, curr_objects, sync_objects, common_obj_ids):
        pass

    @staticmethod
    def _send_message_via_bot(text, delete_previous=False, save_msg_to_db=True):
        request = 'http://127.0.0.1:5000/send_message/'
        request += f'?chat_id={config.ALEXX_TG_CHAT_ID}'
        request += f'&text={text}'
        if delete_previous:
            request += f'&delete_previous=true'
        if save_msg_to_db:
            request += f'&save_msg_to_db=true'
        try:
            requests.post(request)
        except requests.exceptions.ConnectionError:
            print('Не удалось соединиться с ядром бота')

    @staticmethod
    def _to_dict_by_id(lst: list):
        return {obj.id: obj for obj in lst}

    def _get_subtasks(self, task: ExtendedTask):
        return [self.tasks[sub] for sub in self.tasks if self.tasks[sub].parent_id == task.id]

    @staticmethod
    def _tasks_by_project_to_string(tasks_by_projects_list, header: str):
        out = f'<b>{header}</b>\n\n'
        for project_name in tasks_by_projects_list:
            out += f'\U0001F4CB {project_name}\n'
            for goal in tasks_by_projects_list[project_name]:
                out += f'    \U0001f539 <a href="{goal.url}">{goal.content}</a>\n'
            out += '\n'
        return out

    def _is_task_in_correct_state(self):
        pass

    def _get_goals_with_subtasks(self):
        goals = [self.tasks[task] for task in self.tasks if config.goal_label_name in self.tasks[task].labels]
        return tuple(zip(goals, [self._get_subtasks(goal) for goal in goals]))

    def _check_success_label(self, tasks):
        return self._check_label_among_tasks(tasks, config.success_label_name)

    @staticmethod
    def _check_label_among_tasks(tasks, label):
        return [label in task.labels for task in tasks]

    def _filter_goals(self, subtasks_filter: Callable):
        out = defaultdict(list)
        for goal, subtasks in self.goals_with_subtasks:

            filtered_subs = any(subtasks_filter(subtasks))

            if not filtered_subs and goal.priority in (3, 4):
                project = self.projects[goal.project_id]
                out[project.name].append(goal)

        return out

    def _sync_todo_tasks(self):
        return self._to_dict_by_id(self._extend_tasks(self.rest_api.get_tasks()))

    def _sync_done_tasks_by_project(self, project_id):
        return self.sync_api.items_archive.for_project(project_id).items()

    def _sync_projects(self):
        return self._to_dict_by_id(self.rest_api.get_projects())

    def _sync_labels(self):
        return self._to_dict_by_id(self.rest_api.get_labels())

    def _sync_done_tasks(self, projects):
        done_tasks = []
        for project_id in projects:
            done_tasks.extend([ExtendedTask(task.data) for task in self._sync_done_tasks_by_project(project_id)])

        return self._to_dict_by_id(done_tasks)

    def _sync_activity(self):
        # This is dumb! requests.get does not work! But curl does.
        res = os.popen(f'curl https://api.todoist.com/sync/{config.TODOIST_API_VERSION}/activity/get '
                       f'-H "Authorization: Bearer {self.token}"').read()
        all_events = json.loads(res)['events']

        res = {}
        for event in all_events:
            event['is_completed'] = True if event['event_type'] == 'completed' else False
            event['is_deleted'] = True if event['event_type'] == 'deleted' else False
            res[event.object_id] = event

        return res

    @staticmethod
    def _extend_tasks(tasks: Iterable[Task]) -> List[ExtendedTask]:
        return [ExtendedTask(task) for task in tasks]

    def _get_tasks_diff(self, tasks_dict, tasks_ids):
        res = set()
        for task_id in tasks_ids:
            for key in self.tasks[task_id].__dict__:
                if self.tasks[task_id].__dict__[key] != tasks_dict['tasks'][task_id].__dict__[key]:
                    res.add(task_id)
        return res
