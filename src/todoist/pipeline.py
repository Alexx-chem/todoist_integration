from requests.exceptions import ConnectionError
from todoist_api_python.models import Due
from typing import Dict, List

from src.functions import set_db_timezone, send_message_via_bot, save_items_to_db, convert_dt
from src.todoist.entity_managers import get_new_entity_managers
from src.todoist import init_db, GTDHandler
from src.todoist.planner import Planner
from src.logger import get_logger


import config

logger = get_logger(__name__, 'console', logging_level=config.GLOBAL_LOG_LEVEL)


class Pipeline:

    def __init__(self, localize_db_timezone: bool = True):

        self.delete_prev_messages = True
        self.planner = Planner()

        self.tasks_manager = None
        self.projects_manager = None
        self.sections_manager = None
        self.labels_manager = None
        self.events_manager = None

        self._set_managers()

        self.gtd_handler = GTDHandler(self.tasks_manager,
                                      self.projects_manager)

        self._log_prefix = self.__class__.__name__

        if localize_db_timezone:
            set_db_timezone()

    def _set_managers(self):
        managers = get_new_entity_managers()
        self.__managers_names = []
        for entity_name in managers:
            manager_name = f'{entity_name}_manager'
            self.__managers_names.append(manager_name)
            self.__dict__[manager_name] = managers[entity_name]()

    def refresh_plans(self):
        self.tasks_manager.load_items()
        reports = self.planner.refresh_plans(self.tasks_manager.current)
        delete_previous = True
        for horizon in reports:
            report_text = self._format_report(reports[horizon], horizon)
            logger.info(f'{self._log_prefix} - {report_text}')
            logger.info(f'{self._log_prefix} -Sending message via bot')
            try:
                response = send_message_via_bot(report_text, delete_previous=delete_previous, save_msg_to_db=False)
                logger.info(f'{self._log_prefix} - Message sent, response code: {response.status_code}')
            except ConnectionError as e:
                logger.error(f'{self._log_prefix} - Failed to send a message via bot: {e}')
            delete_previous = False

    @staticmethod
    def _format_report(report, horizon, html=True):
        report_text = f"{horizon.capitalize()} plan report"
        if html:
            report_text = "<b>" + report_text + "</b>"

        report_text += '\n\n\n'

        for section in report:
            report_text += report[section]['title'] + '\n'
            if html:
                report_text += config.PLANNER_REPORT_SECTIONS_MARKS[section] + ' '
            report_text += str(report[section]['number']) + '\n\n'

        return report_text

    def get_plan_report(self, horizon):
        return self.planner.plans[horizon].report()

    def handle_changes(self, send_warnings_via_bot=False):
        self.delete_prev_messages = True

        self.tasks_manager.load_items()
        self.events_manager.load_items()

        self.tasks_manager.sync_items()
        self.events_manager.sync_items()
        self.projects_manager.sync_items()

        parsing_res = self.gtd_handler.handle_projects()

        if send_warnings_via_bot and parsing_res:
            for project_parsing_res in parsing_res.values():
                if project_parsing_res['warnings']:
                    self._send_parsing_warnings_via_bot(project_parsing_res['warnings'],
                                                        scope='project')

                goals_warnings = project_parsing_res['goals'].get('warnings')
                if goals_warnings:
                    self._send_parsing_warnings_via_bot(goals_warnings,
                                                        scope='goals')

        new_last_events_for_tasks = self.events_manager.new_last_event_for_task_by_date

        for status in new_last_events_for_tasks:
            events = new_last_events_for_tasks[status]
            if events:
                tasks_to_update = {}
                tasks_to_insert = {}
                for task_id in events:
                    # Task is new or uncompleted, but so old, that it is not present in the DB
                    if task_id not in self.tasks_manager.current:
                        logger.debug(f"Task {task_id} is not in current tasks")
                        task = self.tasks_manager.get_item_from_api(task_id)
                        if task is not None:
                            tasks_to_insert[task_id] = task
                        else:
                            logger.warning(f"Task {task_id} can't be processed, because it was completed or deleted, "
                                           f"and it is too old to be in current tasks. Skipping")
                            continue
                    else:
                        task = self.tasks_manager.synced.get(task_id)

                        if task is None:
                            # If the task is not in synced -- it is completed or deleted
                            logger.debug(f"Task {task_id} is not in synced tasks, updating from events")
                            task = self.update_current_task_from_events(task_id)

                        tasks_to_update[task_id] = task

                    logger.debug(f'{self._log_prefix} - Passing {status} task {task.id} to the Planner')
                    self.planner.process_task(task, status)

                if tasks_to_update:
                    save_items_to_db(entity=self.tasks_manager.entity_name,
                                     attrs=self.tasks_manager.attrs,
                                     items=tasks_to_update,
                                     save_mode='update')

                if tasks_to_insert:
                    save_items_to_db(entity=self.tasks_manager.entity_name,
                                     attrs=self.tasks_manager.attrs,
                                     items=tasks_to_insert,
                                     save_mode='increment')

        self.save_new_events_to_db()

        logger.info(f'{self._log_prefix} - Task changes processed')
        for status, events in new_last_events_for_tasks.items():
            if len(events) > 0:
                logger.debug(f'{status}:')
                for event in events.values():
                    logger.debug(f'   {event.object_id}: {event.extra_data["content"]}')

    def load_all_items(self):
        for manager_name in self.__managers_names:
            self.load_entity_items(manager_name)

    def load_entity_items(self, manager_name: str):
        try:
            self.__dict__[manager_name].load_items()
        except Exception as e:
            logger.error(f'{self._log_prefix} - DB error. {e}')

    def sync_all_items(self):
        for manager_name in self.__managers_names:
            manager = self.__dict__[manager_name]
            manager.sync_items()

    def _get_tasks_diff(self, common_task_ids):

        res = set()

        for task_id in common_task_ids:
            if self.tasks_manager.get_task_diff_by_id(task_id):
                res.add(task_id)

        return res

    def save_new_events_to_db(self):
        events_manager = self.events_manager
        if events_manager.new:
            save_items_to_db(entity=events_manager.entity_name,
                             attrs=events_manager.attrs,
                             items=events_manager.new,
                             save_mode='increment')

    def update_current_task_from_events(self, task_id):
        self.events_manager.sync_items()
        task_events = self.events_manager.synced_by_object_id(task_id)
        task_events.sort(key=lambda x: x.event_date)

        task = self.tasks_manager.current[task_id]
        for event in task_events:
            if event.event_type == 'deleted':
                task.is_deleted = True
                return task

            if event.event_type == 'completed':
                task.is_completed = True

            if event.event_type == 'uncompleted':
                task.is_completed = False

            if event.event_type == 'updated':
                for attr in ('content', 'due_date', 'description'):
                    if event.extra_data.get(f'last_{attr}') is not None:
                        if attr == 'due_date':
                            event_datetime_str = event.extra_data.get(attr)
                            if event_datetime_str is None:
                                due = None
                            else:
                                event_datetime = convert_dt(event_datetime_str)
                                event_date_str = event_datetime.date().strftime(config.TODOIST_DATE_FORMAT)
                                due = Due(date=event_date_str,
                                          string='',
                                          datetime=event_datetime_str,
                                          is_recurring=False)
                            task.due = due
                        else:
                            task.__dict__[attr] = event.extra_data[attr]

        return task

    def init_db(self):
        self.create_tables_if_not_exist()
        self.fill_tables_if_empty()

    def create_tables_if_not_exist(self):
        pass

    @property
    def _get_managers(self) -> Dict:
        return {manager_name: self.__dict__[manager_name] for manager_name in self.__managers_names}

    def fill_tables_if_empty(self):
        init_db.fill_item_tables_from_scratch(managers=self._get_managers, check=True)

    def _send_parsing_warnings_via_bot(self, warnings: List, scope: str):
        warns_text = '\n'.join(warnings)
        send_message_via_bot(text=f"Bad planned {scope}\n\n{warns_text}",
                             delete_previous=self.delete_prev_messages)
        self.delete_prev_messages = False
