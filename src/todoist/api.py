import joblib
import inspect
from todoist_api_python.api import TodoistAPI as Rest_API, Task  # , Project, Label
from todoist.api import TodoistAPI as Sync_API
from collections import defaultdict
from typing import Callable, Iterable, List, Dict, Set
import requests
from time import sleep

from db_worker import DBWorker

from src.todoist.extended_task import ExtendedTask
from src.todoist.planner import Planner

from src.logger import get_logger
import config


logger = get_logger(__name__, 'console', config.GLOBAL_LOG_LEVEL)


class TodoistApi:
    def __init__(self, api_token):
        logger.debug("TodoistApi init")
        self.rest_api = Rest_API(api_token)
        self.sync_api = Sync_API(api_token, api_version=config.TODOIST_API_VERSION)
        self.token = api_token

    def run(self):
        try:
            logger.debug("Loading objects")
            self._load_all_objects()

        except (FileNotFoundError, Exception) as e:
            logger.warning(e)
            self._fill_objects_from_api()

        else:
            self.sync_all_objects()

        self._save_all_objects_to_file()

    def _save_all_objects_to_file(self):
        scope = {collection: vars(self)[collection] for collection in self.OBJECTS_COLLECTION_NAMES}
        joblib.dump(scope, 'todoist_scope')

    def _save_all_objects_to_db(self, target: tuple = ('db',)):
        scope = {collection: vars(self)[collection] for collection in self.OBJECTS_COLLECTION_NAMES}
        for collection in self.OBJECTS_COLLECTION_NAMES:
            DBWorker.input()

    def _load_all_objects(self):
        scope = joblib.load('todoist_scope')
        vars(self).update(scope)

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
        vars(self).update(scope)
        self._save_all_objects_to_file()

    def _process_scope_diff(self, scope):

        task_to_action_map = []

        # Completed tasks
        completed_task_ids = self.tasks.keys() & scope['events']['completed'].keys()
        logger.debug(f'completed_task_ids {completed_task_ids}')
        task_to_action_map.extend([(task_id, 'completed') for task_id in completed_task_ids])

        # Deleted tasks
        deleted_task_ids = (self.tasks.keys() - scope['tasks'].keys()) & scope['events']['deleted'].keys()
        logger.debug(f'deleted_task_ids {deleted_task_ids}')
        task_to_action_map.extend([(task_id, 'deleted') for task_id in deleted_task_ids])

        # Tasks present only in synced scope, not in local
        new_and_uncompleted_task_ids = scope['tasks'].keys() - self.tasks.keys()

        # Newly created tasks
        new_task_ids = new_and_uncompleted_task_ids & scope['events']['added'].keys()
        logger.debug(f'new_task_ids {new_task_ids}')
        task_to_action_map.extend([(task_id, 'created') for task_id in new_task_ids])

        # Uncompleted tasks
        uncompleted_task_ids = new_and_uncompleted_task_ids & scope['events']['uncompleted'].keys()
        logger.debug(f'uncompleted_task_ids {uncompleted_task_ids}')
        task_to_action_map.extend([(task_id, 'uncompleted') for task_id in uncompleted_task_ids])

        # Tasks, present in both synced and local scopes
        common_task_ids = scope['tasks'].keys() & self.tasks.keys()  # Tasks present both in local and synced scopes

        # Tasks, modified in comparison
        modified_tasks = self._get_tasks_diff(scope, common_task_ids)
        logger.debug(f'modified_tasks: {modified_tasks}')

        task_to_action_map.extend([(task_id, 'modified') for task_id in modified_tasks])

        for task_id, action in task_to_action_map:

            if action in ("completed", "deleted"):
                task = self.tasks[task_id]
            else:
                task = scope['tasks'][task_id]

            self.planner.process_task(task, action)

    def refresh_plans(self):
        reports = self.planner.refresh_plans()
        delete_previous = True
        for horizon in reports:
            report_text = self._format_report(reports[horizon], horizon)
            logger.info(report_text)
            self._send_message_via_bot(report_text, delete_previous=delete_previous)
            delete_previous = False

    @staticmethod
    def _format_report(report, horizon, html=True):
        report_text = f"Report for {horizon} plan:\n\n\n"
        if html:
            report_text = "<b>" + report_text + "</b>"

        for section in report:
            if html:
                report_text += config.report_sections_marks[section] + ' '
            report_text += report[section] + '\n\n'

        return report_text

    def get_plan_report(self, horizon):
        return self.planner.plans[horizon].report()

    @staticmethod
    def _send_message_via_bot(text, delete_previous=False, save_msg_to_db=True):
        request = 'http://127.0.0.1:5000/send_message/'
        request += f'?chat_id={config.ALEXX_TG_CHAT_ID}'
        request += f'&text={text}'
        request += f'&delete_previous=true' if delete_previous else ''
        request += f'&save_msg_to_db=true' if save_msg_to_db else ''
        try:
            requests.post(request)
        except requests.exceptions.ConnectionError:
            logger.error('Connection to Telegram Bot Core was unsuccessful')

    @staticmethod
    def _to_dict_by_id(lst: Iterable):
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

    def _sync_todo_tasks(self) -> Dict:
        logger.debug(inspect.currentframe().f_code.co_name)
        try:
            return self._to_dict_by_id(self._extend_tasks(self.rest_api.get_tasks()))
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Sync error. {e}')
            return self.tasks

    def _sync_done_tasks_by_project(self, project_id: str) -> List:
        logger.debug(inspect.currentframe().f_code.co_name)
        try:
            return self.sync_api.items_archive.for_project(project_id).items()
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Sync error. {e}')
            return []

    def _sync_projects(self) -> Dict:
        logger.debug(inspect.currentframe().f_code.co_name)
        try:
            return self._to_dict_by_id(self.rest_api.get_projects())
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Sync error. {e}')
            return self.projects

    def _sync_labels(self) -> Dict:
        logger.debug(inspect.currentframe().f_code.co_name)
        try:
            return self._to_dict_by_id(self.rest_api.get_labels())
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Sync error. {e}')
            return self.labels

    def _sync_done_tasks(self, projects: List) -> Dict:
        # Heavy operation, avoid to use
        logger.debug(inspect.currentframe().f_code.co_name)
        done_tasks = []
        for project_id in projects:
            done_tasks.extend([ExtendedTask(task.data) for task in self._sync_done_tasks_by_project(project_id)])
            sleep(5)

        return self._to_dict_by_id(done_tasks)

    @staticmethod
    def _extend_tasks(tasks: Iterable[Task]) -> List[ExtendedTask]:
        return [ExtendedTask(task) for task in tasks]

    def _get_tasks_diff(self, tasks_dict: Dict, tasks_ids: Iterable) -> Set:
        res = set()
        for task_id in tasks_ids:
            for property_key in vars(self.tasks[task_id]):
                old_property_value = vars(self.tasks[task_id])[property_key]
                new_property_value = vars(tasks_dict['tasks'][task_id])[property_key]
                if old_property_value != new_property_value:
                    if property_key == 'due':
                        if self._due_same_except_string(old_property_value, new_property_value):
                            logger.debug(f'due.string changed: {self.tasks[task_id].content}')
                            continue

                    res.add(task_id)
        return res

    @staticmethod
    def _due_same_except_string(task_due_1, task_due_2) -> bool:
        # Patch. Field 'due.string' is changing at the server side at midnight!
        if None not in (task_due_1, task_due_2):
            return all([vars(task_due_1)[key] == vars(task_due_2)[key]
                        for key in vars(task_due_1) if key != 'string'])

        return False
