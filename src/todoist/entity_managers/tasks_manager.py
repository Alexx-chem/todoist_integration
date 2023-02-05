from typing import Iterable, List, Dict, Union
from time import sleep

from .entity_manager_abc import EntityManagerABC
from src.todoist import ExtendedTask


class TasksManager(EntityManagerABC):

    def __init__(self):
        EntityManagerABC.__init__(self, 'tasks')

    def _get_raw_items_from_api(self):
        return self.rest_api.get_tasks()

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

        return self._objects_to_dict_by_id(done_tasks)

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

    @property
    def updated_diff(self):
        updated = super().updated_diff
        for task_id in updated:

            if property_key == 'due':
                if self._due_same_except_string(old_property_value, new_property_value):
                    self.logger.debug(f'due.string changed: {self.tasks[task_id].content}')
                    continue