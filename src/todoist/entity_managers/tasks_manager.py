from todoist_api_python.models import Task
from requests.exceptions import HTTPError
from typing import Iterable, List, Dict
from time import sleep

import config
from src.functions import convert_dt, unpack_chained_attr
from .base_entity_manager import BaseEntityManager, logger
from src.todoist import ExtendedTask
from . import ENTITY_CONFIG


class TasksManager(BaseEntityManager):

    _entity_name = 'tasks'
    _entity_type = ENTITY_CONFIG[_entity_name]['entity_type']
    _attrs = ENTITY_CONFIG[_entity_name]['attrs']

    def __init__(self):
        BaseEntityManager.__init__(self)

    def sync_tasks_by_ids(self, ids_list: List) -> Dict:
        return {task_id: self._get_item_from_api(task_id) for task_id in ids_list}

    def _get_items_from_api(self):
        return self._to_dict_by_id(self._extend_tasks(self.api.rest_api.get_tasks()))

    def _get_item_from_api(self, _id) -> Dict[str, _entity_type]:
        try:
            task = self._extend_task(self.api.rest_api.get_task(task_id=_id))
        except HTTPError:
            logger.error(f'Could not get task from api by id {_id}')
            task = None
        return task

    def _extend_tasks(self, tasks: Iterable[Task]) -> List[_entity_type]:
        return [self._extend_task(task) for task in tasks]

    @staticmethod
    def _extend_task(task: Task) -> _entity_type:
        return ExtendedTask.extend(task)

    def _sync_done_tasks(self, projects: List) -> Dict:
        # Heavy operation, avoid to use
        done_tasks = []
        for project_id in projects:         
            done_tasks.extend([ExtendedTask.extend(task.data) for task in self._sync_done_tasks_by_project(project_id)])
            sleep(5)  # in order to prevent DoS. Better rework!

        return self._to_dict_by_id(done_tasks)

    def _sync_done_tasks_by_project(self, project_id: str) -> List:
        try:
            return self.api.sync_api.items_archive.for_project(project_id).items()
        except ConnectionError as e:
            logger.error(f'{self._logger_prefix} - Sync error. {e}')
            return []

    def get_tasks_diff(self, task_ids):
        return {task_id: self.get_task_diff_by_id(task_id) for task_id in task_ids}

    def get_task_diff_by_id(self, task_id: str) -> Dict:
        current_task = self.current.get(task_id)
        synced_task = self.synced.get(task_id)

        res = {}

        if None not in (current_task, synced_task):
            for property_key in self._attrs:
                old_property_value = unpack_chained_attr(current_task, property_key.split('.'))
                new_property_value = unpack_chained_attr(synced_task, property_key.split('.'))
                if old_property_value != new_property_value:
                    if property_key == 'due':
                        if self._due_same_except_string(old_property_value, new_property_value):
                            logger.debug(f'{self._logger_prefix} - due.string changed: {current_task.content}')
                            continue

                    res[property_key] = {'old': old_property_value,
                                         'new': new_property_value}
        return res

    @staticmethod
    def _due_same_except_string(task_due_1, task_due_2) -> bool:
        # Patch. Field 'due.string' is changing at the server side at midnight!
        if None not in (task_due_1, task_due_2):
            return all([vars(task_due_1)[key] == vars(task_due_2)[key]
                        for key in vars(task_due_1) if key != 'string'])

        return False

    @property
    def synced_goals(self):
        return {task_id: task for task_id, task in self.synced.items() if config.SPECIAL_LABELS['GOAL'] in task.labels}

    @staticmethod
    def get_extreme_due_task(tasks: Dict, latest=False):

        extreme_task = None

        # Inefficient, can be made in one pass
        for current_task in tasks.values():
            if current_task.due is not None:
                if extreme_task is None:
                    extreme_task = current_task
                else:
                    extreme_date_converted = convert_dt(extreme_task.due.date, str_type='date')
                    current_date_converted = convert_dt(current_task.due.date, str_type='date')

                    if extreme_date_converted != current_date_converted:
                        # If latest => taking task which is later, otherwise taking earlier
                        if extreme_date_converted < current_date_converted:
                            extreme_task = (extreme_task, current_task)[latest]
                        else:
                            extreme_task = (current_task, extreme_task)[latest]
                    else:
                        if extreme_task.due.datetime is None:
                            extreme_task = current_task if current_task.due.datetime is not None else extreme_task
                        else:
                            extreme_datetime_converted = convert_dt(extreme_task.due.datetime)
                            if current_task.due.datetime is not None:
                                current_datetime_converted = convert_dt(current_task.due.datetime)
                                # If latest => taking task which is later, otherwise taking earlier
                                if extreme_datetime_converted < current_datetime_converted:
                                    extreme_task = (extreme_task, current_task)[latest]
                                else:
                                    extreme_task = (current_task, extreme_task)[latest]

        return extreme_task
