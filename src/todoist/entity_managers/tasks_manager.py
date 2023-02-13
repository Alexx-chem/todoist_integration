from typing import Iterable, List, Dict
from todoist_api_python.models import Task
from time import sleep

from .entity_manager_abs import AbstractEntityManager
from src.todoist import ExtendedTask
from . import ENTITY_CONFIG


class TasksManager(AbstractEntityManager):

    _entity_name = 'tasks'
    _entity_type = ENTITY_CONFIG[_entity_name]['entity_type']
    _attrs = ENTITY_CONFIG[_entity_name]['attrs'].keys()

    def __init__(self):
        AbstractEntityManager.__init__(self)

    def load_items(self, *args, **kwargs):
        return super().load_items(*args, **kwargs)

    def _get_items_from_api(self):
        return self._to_dict_by_id(self._extend_tasks(self.rest_api.get_tasks()))

    def _get_item_from_api(self, _id) -> Dict[str, _entity_type]:
        ext_task = self._extend_task(self.rest_api.get_task(task_id=_id))
        return {ext_task.id: ext_task}

    def _extend_tasks(self, tasks: Iterable[Task]) -> List[_entity_type]:
        return [self._extend_task(task) for task in tasks]

    @staticmethod
    def _extend_task(task: Task) -> _entity_type:
        return ExtendedTask.extend(task)

    def get_filtered_new_items(self, *args, **kwargs):
        pass

    def _process_update(self, items):
        pass

    def _sync_done_tasks(self, projects: List) -> Dict:
        # Heavy operation, avoid to use
        done_tasks = []
        for project_id in projects:         
            done_tasks.extend([ExtendedTask(task.data) for task in self._sync_done_tasks_by_project(project_id)])
            sleep(5)  # in order to prevent DoS, better rework!

        return self._to_dict_by_id(done_tasks)

    def _sync_done_tasks_by_project(self, project_id: str) -> List:
        try:
            return self.sync_api.items_archive.for_project(project_id).items()
        except ConnectionError as e:
            self.logger.error(f'Sync error. {e}')
            return []

    @staticmethod
    def _due_same_except_string(task_due_1, task_due_2) -> bool:
        # Patch. Field 'due.string' is changing at the server side at midnight!
        if None not in (task_due_1, task_due_2):
            return all([vars(task_due_1)[key] == vars(task_due_2)[key]
                        for key in vars(task_due_1) if key != 'string'])

        return False

    def get_tasks_diff(self, task_ids):
        return {task_id: self.get_task_diff_by_id(task_id) for task_id in task_ids}

    def get_task_diff_by_id(self, task_id: str) -> Dict:
        current_task = self.get_current_item_by_id(task_id)
        synced_task = self.get_synced_item_by_id(task_id)

        res = {}

        for property_key in vars(Task):
            old_property_value = vars(current_task)[property_key]
            new_property_value = vars(synced_task)[property_key]
            if old_property_value != new_property_value:
                if property_key == 'due':
                    if self._due_same_except_string(old_property_value, new_property_value):
                        self.logger.debug(f'due.string changed: {current_task.content}')
                        continue

                res[property_key] = {'old': old_property_value,
                                     'new': new_property_value}
        return res

    def _get_subtasks(self, task: ExtendedTask):
        return [self._current_items[sub]
                for sub in self._current_items
                if self._current_items[sub].parent_id == task.id]
