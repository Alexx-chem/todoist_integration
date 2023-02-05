from todoist_api_python.api import Task, Project, Section, Label
from requests.exceptions import ConnectionError
from typing import List, Union

from src.todoist.entity_managers import get_manager
from src.functions import set_db_timezone
from src.logger import get_logger

import config


class Synchronizer:

    def __init__(self, localize_db_timezone: bool = True):

        self.logger = get_logger(self.__class__.__name__, 'console', config.GLOBAL_LOG_LEVEL)

        for entity_name in config.ENTITIES:
            self.managers = {entity_name: get_manager(entity_name)}

        if localize_db_timezone:
            set_db_timezone()

    def load_all_items(self):
        for entity_name in self.managers:
            self.load_entity_items(entity_name)

    def load_entity_items(self, entity_name: str):
        try:
            self.managers[entity_name]._load_items()
        except Exception as e:
            self.logger.error(f'DB error. {e}')

    def sync_all_items(self, sync_mode: str = 'increment'):
        for entity_name in self.managers:
            self.sync_entity_items(entity_name, sync_mode)

    def sync_entity_items(self, entity_name: str, sync_mode: str):
        try:
            self.managers[entity_name]._sync_items(sync_mode=sync_mode)
        except ConnectionError as e:
            self.logger.error(f'Sync error. {e}')

    def process_events_diff(self):

        task_to_action_map = {}

        synced_events = self.managers['events'].synced_by_type

        for event_type in synced_events:
            tasks_to_action = {event.object_id: event_type
                               for event in synced_events[event_type]
                               if event['object_type'] == 'item'}
            self.logger.debug(f'{event_type}_task_ids {tasks_to_action.keys()}')
            task_to_action_map.update(tasks_to_action)

        for task_id, action in task_to_action_map.items():

            # TODO Store all items as {id: item}! In order to make the following requests faster:
            # return difference between current and synced states of an item
            task = self.managers['tasks'].get_task_diff_by_id(task_id)

            # TODO Planned should be separate from Entity Manager (and from API)
            self.planner.process_task(task, action)

    def process_diff(self):
        # TODO Rework needed
        task_to_action_map = []

        current_tasks = self.managers['tasks'].current_items
        synced_tasks = self.managers['tasks'].synced_items

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
