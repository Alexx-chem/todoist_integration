import joblib
import json
import os
from operator import itemgetter
import inspect
from todoist_api_python.api import TodoistAPI as Rest_API, Task
from todoist.api import TodoistAPI as Sync_API
from collections import defaultdict
from typing import Callable, Iterable, List
import requests
from time import sleep

import config

from src.todoist.extended_task import ExtendedTask
from src.todoist.planner import Planner
from src.functions import set_db_timezone
from src.logger import get_logger


logger = get_logger(__name__, 'console', config.GLOBAL_LOG_LEVEL)


class TodoistApi:

    OBJECTS_COLLECTION_NAMES = ['tasks',
                                'projects',
                                'labels',
                                'events',
                                'goals_with_subtasks']

    def __init__(self, todoist_api_token):
        logger.debug("TodoistApi init")
        self.rest_api = Rest_API(todoist_api_token)
        self.sync_api = Sync_API(todoist_api_token, api_version=config.TODOIST_API_VERSION)
        self.token = todoist_api_token

        self.tasks = None
        self.projects = None
        self.labels = None
        self.events = None

        self.goals_with_subtasks = None

        self.planner = Planner(self)

        set_db_timezone()

    def run(self):
        try:
            logger.debug("Loading objects")
            self._load_all_objects()

        except (FileNotFoundError, Exception) as e:
            logger.warning(e)
            self._fill_objects_from_api()
            self.goals_with_subtasks = self._get_goals_with_subtasks()

        else:
            self.sync_all_objects()

        self._save_all_objects()

    def _save_all_objects(self):
        scope = {collection: self.__dict__[collection] for collection in self.OBJECTS_COLLECTION_NAMES}
        joblib.dump(scope, 'todoist_scope')

    def _load_all_objects(self):
        scope = joblib.load('todoist_scope')
        self.__dict__.update(scope)

    def _fill_objects_from_api(self):
        self.tasks = self._sync_todo_tasks()
        self.projects = self._sync_projects()
        self.labels = self._sync_labels()
        self.events = self._sync_events()

    def sync_all_objects(self):
        logger.debug("sync_all_objects")

        tasks = self._sync_todo_tasks()
        projects = self._sync_projects()

        scope = {
            'tasks': tasks,
            'projects': projects,
            'labels': self._sync_labels(),
            'events': self._sync_events()
        }

        self._process_scope_diff(scope)
        self.__dict__.update(scope)
        self.goals_with_subtasks = self._get_goals_with_subtasks()
        self._save_all_objects()

    def _process_scope_diff(self, scope):

        task_to_action_map = []

        # Tasks present only in local scope, not in synced
        stale_task_ids = self.tasks.keys() - scope['tasks'].keys()
        print('stale_task_ids', stale_task_ids)

        # Completed tasks
        completed_task_ids = stale_task_ids & scope['events']['completed'].keys()
        print('completed_task_ids', completed_task_ids)
        task_to_action_map.extend([(task_id, 'completed') for task_id in completed_task_ids])

        # Deleted tasks
        deleted_task_ids = stale_task_ids & scope['events']['deleted'].keys()
        print('deleted_task_ids', deleted_task_ids)
        task_to_action_map.extend([(task_id, 'deleted') for task_id in deleted_task_ids])

        print('len stale', len(stale_task_ids))
        print('len completed + deleted', len(completed_task_ids | deleted_task_ids))

        # Tasks present only in synced scope, not in local
        new_and_uncompleted_task_ids = scope['tasks'].keys() - self.tasks.keys()
        print('new_and_uncompleted_task_ids', new_and_uncompleted_task_ids)

        # Newly created tasks
        new_task_ids = new_and_uncompleted_task_ids & scope['events']['added'].keys()
        print('new_task_ids', new_task_ids)
        task_to_action_map.extend([(task_id, 'created') for task_id in new_task_ids])

        # Uncompleted tasks
        uncompleted_task_ids = new_and_uncompleted_task_ids & scope['events']['updated'].keys()
        print('uncompleted_task_ids', uncompleted_task_ids)
        task_to_action_map.extend([(task_id, 'undone') for task_id in uncompleted_task_ids])

        print('len new and uncompleted', len(new_and_uncompleted_task_ids))
        print('len new + uncompleted', len(new_task_ids | uncompleted_task_ids))

        # Tasks, present in both synced and local scopes
        common_task_ids = scope['tasks'].keys() & self.tasks.keys()  # Tasks present both in local and synced scopes
        # print('common_task_ids', common_task_ids)

        # Tasks, modified in comparison
        modified_tasks = self._get_tasks_diff(scope, common_task_ids)
        print('modified_tasks', modified_tasks)

        task_to_action_map.extend([(task_id, 'modified') for task_id in modified_tasks])

        for task_id, action in task_to_action_map:

            if action in ("completed", "deleted"):
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
            logger.error('Connection to Telegram Bot Core is unsuccessful')

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
        logger.debug(inspect.currentframe().f_code.co_name)
        return self._to_dict_by_id(self._extend_tasks(self.rest_api.get_tasks()))

    def _sync_done_tasks_by_project(self, project_id):
        logger.debug(inspect.currentframe().f_code.co_name)
        return self.sync_api.items_archive.for_project(project_id).items()

    def _sync_projects(self):
        logger.debug(inspect.currentframe().f_code.co_name)
        return self._to_dict_by_id(self.rest_api.get_projects())

    def _sync_labels(self):
        logger.debug(inspect.currentframe().f_code.co_name)
        return self._to_dict_by_id(self.rest_api.get_labels())

    def _sync_done_tasks(self, projects):
        # Heavy operation, avoid to use
        logger.debug(inspect.currentframe().f_code.co_name)
        done_tasks = []
        for project_id in projects:
            done_tasks.extend([ExtendedTask(task.data) for task in self._sync_done_tasks_by_project(project_id)])
            sleep(5)

        return self._to_dict_by_id(done_tasks)

    def _sync_events(self):
        logger.debug(inspect.currentframe().f_code.co_name)
        # This is dumb! requests.get does not work! But curl does.
        # limit=100 is the max value for one page. Documented "cursor" and "has_more" fields are absent in the response
        response = os.popen(f'curl https://api.todoist.com/sync/{config.TODOIST_API_VERSION}/activity/get?limit=100 '
                            f'-H "Authorization: Bearer {self.token}"')

        activity = json.loads(response.read())
        all_events = activity['events']
        all_events_sorted_by_date = sorted(all_events, key=itemgetter('event_date'), reverse=True)

        res = defaultdict(dict)
        seen = set()

        for event in all_events_sorted_by_date:
            event['is_completed'] = event['event_type'] == 'completed'
            event['is_deleted'] = event['event_type'] == 'deleted'
            if event['object_id'] not in seen:
                res[event['event_type']][event['object_id']] = event
                seen.add(event['object_id'])

        return res

    @staticmethod
    def _extend_tasks(tasks: Iterable[Task]) -> List[ExtendedTask]:
        return [ExtendedTask(task) for task in tasks]

    def _get_tasks_diff(self, tasks_dict, tasks_ids):
        res = {}
        for task_id in tasks_ids:
            for key in self.tasks[task_id].__dict__:
                if self.tasks[task_id].__dict__[key] != tasks_dict['tasks'][task_id].__dict__[key]:
                    res[task_id] = {}
        return res
