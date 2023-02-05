from todoist_api_python.api import Task, Project, Section, Label
from requests.exceptions import ConnectionError
from typing import List, Union, Iterable
from collections import defaultdict

from src.todoist.entity_managers import TasksManager, ProjectsManager, SectionsManager, LabelsManager, EventsManager
from src.todoist.entity_managers.todoist_event import Event
from src.functions import set_db_timezone
from src.logger import get_logger


import config


class Synchronizer:

    def __init__(self, localize_db_timezone: bool = True):

        self.logger = get_logger(self.__class__.__name__, 'console', config.GLOBAL_LOG_LEVEL)

        self.managers = {'tasks': TasksManager(),
                         'projects': ProjectsManager(),
                         'sections': SectionsManager(),
                         'labels': LabelsManager(),
                         'events': EventsManager()}

        if localize_db_timezone:
            set_db_timezone()

    def diff_sync(self):

        events_manager = self.managers['events']
        events_manager.load_items()
        events_manager.sync_items()

        tasks_manager = self.managers['tasks']

        new_events = events_manager.new_by_type

        for event_type in new_events:
            task_ids = [event.object_id
                        for event in new_events[event_type]
                        if event.object_type == 'item']








    def load_all_items(self):
        for entity_name in self.managers:
            self.load_entity_items(entity_name)

    def load_entity_items(self, entity_name: str):
        try:
            self.managers[entity_name].load_items()
        except Exception as e:
            self.logger.error(f'DB error. {e}')

    def sync_all_items(self, sync_mode: str = 'increment'):
        for entity_name in self.managers:
            self.sync_entity_items(entity_name, sync_mode)

    # TODO Rework needed
    def process_diff(self):

        task_to_action_map = []

        current_tasks = self.managers['tasks'].current
        synced_tasks = self.managers['tasks'].synced

        new_events_completed = self.managers['events'].synced_completed

        # Completed tasks
        completed_task_ids = current_tasks.keys() & new_events_completed.keys()
        self.logger.debug(f'completed_task_ids {completed_task_ids}')
        task_to_action_map.extend([(task_id, 'completed') for task_id in completed_task_ids])

        # Deleted tasks
        deleted_task_ids = (self.tasks.keys() - scope['tasks'].keys()) & scope['events']['deleted'].keys()
        self.logger.debug(f'deleted_task_ids {deleted_task_ids}')
        task_to_action_map.extend([(task_id, 'deleted') for task_id in deleted_task_ids])

        # Tasks present only in synced scope, not in local
        new_and_uncompleted_task_ids = scope['tasks'].keys() - self.tasks.keys()

        # Newly created tasks
        new_task_ids = new_and_uncompleted_task_ids & scope['events']['added'].keys()
        self.logger.debug(f'new_task_ids {new_task_ids}')
        task_to_action_map.extend([(task_id, 'created') for task_id in new_task_ids])

        # Uncompleted tasks
        uncompleted_task_ids = new_and_uncompleted_task_ids & scope['events']['uncompleted'].keys()
        self.logger.debug(f'uncompleted_task_ids {uncompleted_task_ids}')
        task_to_action_map.extend([(task_id, 'uncompleted') for task_id in uncompleted_task_ids])

        # Tasks, present in both synced and local scopes
        common_task_ids = scope['tasks'].keys() & self.tasks.keys()  # Tasks present both in local and synced scopes

        # Tasks, modified in comparison
        modified_tasks = self._get_tasks_diff(scope, common_task_ids)
        self.logger.debug(f'modified_tasks: {modified_tasks}')

        task_to_action_map.extend([(task_id, 'modified') for task_id in modified_tasks])

        for task_id, action in task_to_action_map:

            if action in ("completed", "deleted"):
                task = self.tasks[task_id]
            else:
                task = scope['tasks'][task_id]

            self.planner.process_task(task, action)
