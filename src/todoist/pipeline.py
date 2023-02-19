from requests.exceptions import ConnectionError

# DON'T DELETE! These are used in dirty eva(i)l hacks
from src.todoist.entity_managers import TasksManager, ProjectsManager, SectionsManager, LabelsManager, EventsManager

from src.functions import set_db_timezone, send_message_via_bot, save_items_to_db
from src.todoist.entity_managers import ENTITY_CONFIG
from src.todoist.planner import Planner
from src.logger import get_logger

import config


class Pipeline:

    def __init__(self, localize_db_timezone: bool = True):

        self.logger = get_logger(self.__class__.__name__, 'console', config.GLOBAL_LOG_LEVEL)

        self.managers = self._get_managers()

        self.planner = Planner()

        if localize_db_timezone:
            set_db_timezone()

    def _get_managers(self):
        return {entity: self._get_manager_by_entity_name(entity) for entity in ENTITY_CONFIG}

    @staticmethod
    def _get_manager_by_entity_name(entity_name):

        assert entity_name in ENTITY_CONFIG.keys(), f'Unknown entity name: {entity_name}'

        if entity_name == 'tasks':
            return TasksManager()
        if entity_name == 'projects':
            return ProjectsManager()
        if entity_name == 'sections':
            return SectionsManager()
        if entity_name == 'labels':
            return LabelsManager()
        if entity_name == 'events':
            return EventsManager()

    def _get_current_entity_scope(self, entity_type):
        self.managers[entity_type].load_items()
        return self.managers[entity_type].current

    def _get_synced_entity_scope(self, entity_type):
        self.managers[entity_type].sync_items()
        return self.managers[entity_type].synced

    def refresh_plans(self):

        reports = self.planner.refresh_plans(self.managers['tasks'].current)
        delete_previous = True
        for horizon in reports:
            report_text = self._format_report(reports[horizon], horizon)
            self.logger.info(report_text)
            self.logger.info('Sending message via bot')
            try:
                response = send_message_via_bot(report_text, delete_previous=delete_previous)
                self.logger.info(f'Message sent, response code: {response.status_code}')
            except ConnectionError as e:
                self.logger.error(f'Failed to send a message via bot: {e}')

    @staticmethod
    def _format_report(report, horizon, html=True):
        report_text = f"Report for {horizon} plan:\n\n\n"
        if html:
            report_text = "<b>" + report_text + "</b>"

        for section in report:
            if html:
                report_text += config.PLANNER_REPORT_SECTIONS_MARKS[section] + ' '
            report_text += report[section] + '\n\n'

        return report_text

    def get_plan_report(self, horizon):
        return self.planner.plans[horizon].report()

    def update_by_events(self):

        events_manager = self.managers['events']
        task_manager = self.managers['tasks']

        task_manager.load_items()
        events_manager.load_items()
        events_manager.sync_items()

        new_last_events_for_tasks = events_manager.new_last_event_for_task_by_date

        for status in new_last_events_for_tasks:
            events = new_last_events_for_tasks[status]
            if events:
                if status in ('completed', 'deleted', 'uncompleted', 'updated'):
                    tasks_to_process = {task_id: task_manager.current[task_id] for task_id in events}
                    for task_id in tasks_to_process:
                        # Hoping we never can get an event for deleted task id!
                        tasks_to_process[task_id].is_deleted = status == 'deleted'

                        if status in ('completed', 'uncompleted'):
                            tasks_to_process[task_id].is_completed = status == 'completed' or \
                                                          not status == 'uncompleted'
                    save_items_to_db(entity=task_manager.entity_name,
                                     attrs=task_manager.attrs,
                                     items=tasks_to_process,
                                     save_mode='update')

                elif status == 'added':
                    tasks_to_process = task_manager.sync_tasks_by_ids(events.keys())
                    save_items_to_db(entity=task_manager.entity_name,
                                     attrs=task_manager.attrs,
                                     items=tasks_to_process,
                                     save_mode='increment')

                else:
                    raise ValueError(f'Unknown task status: {status}')

                save_items_to_db(entity=events_manager.entity_name,
                                 attrs=events_manager.attrs,
                                 items=events,
                                 save_mode='increment')

                for task in tasks_to_process.values():
                    self.planner.process_task(task, status)

        self.logger.info(f'Update by events complete. Updated tasks qty: '
                         f'{sum(len(v) for v in new_last_events_for_tasks.values())}')

    def load_all_items(self):
        for entity_name in self.managers:
            self.load_entity_items(entity_name)

    def load_entity_items(self, entity_name: str):
        try:
            self.managers[entity_name].load_items()
        except Exception as e:
            self.logger.error(f'DB error. {e}')

    def sync_all_items(self):
        for manager in self.managers.values():
            manager.sync_items()

    def process_diff(self):
        # TODO Rework needed

        task_to_action_map = []

        current_tasks = self.managers['tasks'].current
        synced_tasks = self.managers['tasks'].synced

        new_events = self.managers['events'].synced_last_for_item_by_date

        # Completed tasks
        completed_task_ids = current_tasks.keys() & new_events['completed'].keys()
        self.logger.debug(f'completed_task_ids {completed_task_ids}')
        task_to_action_map.extend([(task_id, 'completed') for task_id in completed_task_ids])

        # Deleted tasks
        deleted_task_ids = (current_tasks.keys() - synced_tasks.keys()) & new_events['deleted'].keys()
        self.logger.debug(f'deleted_task_ids {deleted_task_ids}')
        task_to_action_map.extend([(task_id, 'deleted') for task_id in deleted_task_ids])

        # Tasks present only in synced scope, not in local
        new_and_uncompleted_task_ids = synced_tasks.keys() - current_tasks.keys()

        # Newly created tasks
        new_task_ids = new_and_uncompleted_task_ids & new_events['added'].keys()
        self.logger.debug(f'new_task_ids {new_task_ids}')
        task_to_action_map.extend([(task_id, 'created') for task_id in new_task_ids])

        # Uncompleted tasks
        uncompleted_task_ids = new_and_uncompleted_task_ids & new_events['uncompleted'].keys()
        self.logger.debug(f'uncompleted_task_ids {uncompleted_task_ids}')
        task_to_action_map.extend([(task_id, 'uncompleted') for task_id in uncompleted_task_ids])

        # Tasks, present in both synced and local scopes
        common_task_ids = synced_tasks.keys() & current_tasks.keys()  # Tasks present both in local and synced scopes

        # Tasks, modified in comparison
        modified_tasks = self._get_tasks_diff(common_task_ids)
        self.logger.debug(f'modified_tasks: {modified_tasks}')

        task_to_action_map.extend([(task_id, 'modified') for task_id in modified_tasks])

        for task_id, action in task_to_action_map:

            if action in ("completed", "deleted"):
                task = current_tasks[task_id]
            else:
                task = synced_tasks[task_id]

            self.planner.process_task(task, action)

    def _get_tasks_diff(self, common_task_ids):

        res = set()

        for task_id in common_task_ids:
            if self.managers['tasks'].get_task_diff_by_id(task_id):
                res.add(task_id)

        return res
