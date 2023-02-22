from datetime import datetime

from requests.exceptions import ConnectionError
from todoist_api_python.models import Due

from src.todoist.entity_managers import get_managers, TasksManager, ProjectsManager, SectionsManager, LabelsManager, EventsManager
from src.functions import set_db_timezone, send_message_via_bot, save_items_to_db
from src.todoist.planner import Planner
from src.logger import get_logger
from src.todoist import init_db

import config


class Pipeline:

    def __init__(self, localize_db_timezone: bool = True):

        self.logger = get_logger(self.__class__.__name__, 'console', config.GLOBAL_LOG_LEVEL)

        self.managers = get_managers()

        self.planner = Planner()

        if localize_db_timezone:
            set_db_timezone()

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
        report_text = f"{horizon.capitalize()} plan report:\n\n\n"
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
        task_manager.sync_items()

        events_manager.load_items()
        events_manager.sync_items()

        new_last_events_for_tasks = events_manager.new_last_event_for_task_by_date

        for status in new_last_events_for_tasks:
            events = new_last_events_for_tasks[status]
            if events:
                tasks_to_update = {}
                tasks_to_insert = {}
                for task_id in events:
                    # Task is new or uncompleted, but so old, that it is not present in the DB
                    if task_id not in task_manager.current:
                        task = task_manager.get_item_from_api(task_id)
                        tasks_to_insert[task_id] = task

                    else:
                        task = task_manager.synced.get(task_id)
                        if task is None:
                            # If the task is not in synced -- it is completed or deleted
                            task = self.update_current_task_from_events(task_id)

                        task.is_deleted = status == 'deleted'

                        if status == 'completed':
                            due = task.due
                            if due is None or not due.is_recurring:
                                task.is_completed = True

                        if status == 'uncompleted':
                            task.is_completed = False

                        tasks_to_update[task_id] = task

                    self.logger.debug(f'Passing task {task.id} to planner')
                    self.planner.process_task(task, status)

                if tasks_to_update:
                    save_items_to_db(entity=task_manager.entity_name,
                                     attrs=task_manager.attrs,
                                     items=tasks_to_update,
                                     save_mode='update')

                if tasks_to_insert:
                    save_items_to_db(entity=task_manager.entity_name,
                                     attrs=task_manager.attrs,
                                     items=tasks_to_insert,
                                     save_mode='increment')

        self.save_new_events_to_db()

        self.logger.info(f'Update by events complete')
        for status, tasks in new_last_events_for_tasks.items():
            if len(tasks) > 0:
                self.logger.info(f'{status}:')
                for task in tasks.values():
                    self.logger.info(f'   {task.id}: {task.extra_data["content"]}')

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
        """
        Legacy. Maybe not needed
        """

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

            task_planned = self.planner.process_task(task, action)
            self.logger.debug(f'Task {"is" if task_planned else "is not"} planned')

    def _get_tasks_diff(self, common_task_ids):

        res = set()

        for task_id in common_task_ids:
            if self.managers['tasks'].get_task_diff_by_id(task_id):
                res.add(task_id)

        return res

    def save_new_events_to_db(self):
        events_manager = self.managers['events']
        if events_manager.new:
            save_items_to_db(entity=events_manager.entity_name,
                             attrs=events_manager.attrs,
                             items=events_manager.new,
                             save_mode='increment')

    def update_current_task_from_events(self, task_id):
        self.managers['events'].sync_items()
        task_events = self.managers['events'].synced_by_object_id(task_id)
        task_events.sort(key=lambda x: x.event_date)

        known_task_state = self.managers['tasks'].current[task_id]
        for event in task_events:
            for attr in ('content', 'due_date', 'description'):
                if event.extra_data.get(f'last_{attr}') is not None:
                    if attr == 'due_date':
                        event_datetime_str = event.extra_data.get(attr)
                        if event_datetime_str is None:
                            due = None
                        else:
                            event_datetime = datetime.strptime(event_datetime_str, config.TODOIST_DATETIME_FORMAT)
                            event_date_str = event_datetime.date().strftime(config.TODOIST_DATE_FORMAT)
                            due = Due(date=event_date_str,
                                      string='',
                                      datetime=event_datetime_str,
                                      is_recurring=False)
                        known_task_state.due = due
                    else:
                        known_task_state.__dict__[attr] = event.extra_data[attr]

        return known_task_state

    def init_db(self):
        self.create_tables_if_not_exist()
        self.fill_tables_if_empty()

    def create_tables_if_not_exist(self):
        pass

    def fill_tables_if_empty(self):
        init_db.fill_item_tables_from_scratch(managers=self.managers, check=True)
