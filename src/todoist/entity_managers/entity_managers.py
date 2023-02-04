from typing import List, Dict
from requests.exceptions import ConnectionError
from collections import defaultdict
from operator import itemgetter
from datetime import datetime
from time import sleep
import inspect
import json
import os

from db_worker import DBWorker

from src.logger import get_logger
from src.todoist.api import TodoistApi
from src.todoist.extended_task import ExtendedTask
from src.functions import set_db_timezone
from src.todoist.entity_manager_abc import EntityManagerABC
import config

logger = get_logger(__name__, 'console', config.GLOBAL_LOG_LEVEL)


class Synchronizer:

    def __init__(self, localize_db_timezone=True):
        super(EntityManagerABC).__init__()

        for entity_name in config.ENTITIES:
            vars(self)[entity_name] = None
            vars(self)[f'{entity_name}_manager'] = get_manager(entity_name)

        if localize_db_timezone:
            set_db_timezone()

    def full_sync(self, db_save_mode: str = 'soft'):
        for entity_name in config.ENTITIES:
            try:
                vars(self)[f'{entity_name}_manager'].full_sync(db_save_mode=db_save_mode)
            except ConnectionError as e:
                logger.error(f'Sync error. {e}')

    def diff_sync(self):
        pass


def get_manager(entity_name):
    assert entity_name in config.ENTITIES, f'Unknown entity name: {entity_name}'
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


class TasksManager(EntityManagerABC, TodoistApi):
    def __init__(self):
        EntityManagerABC.__init__(self, 'tasks')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def full_sync(self):
        return self._objects_to_dict_by_id(self._extend_tasks(self.rest_api.get_tasks()))

    def diff_sync(self):
        pass

    def _sync_done_tasks(self, projects: List) -> Dict:
        # Heavy operation, avoid to use
        logger.debug(inspect.currentframe().f_code.co_name)
        done_tasks = []
        for project_id in projects:
            done_tasks.extend([ExtendedTask(task.data) for task in self._sync_done_tasks_by_project(project_id)])
            sleep(5)  # in order to prevent DoS

        return self._objects_to_dict_by_id(done_tasks)

    def _sync_done_tasks_by_project(self, project_id: str) -> List:
        logger.debug(inspect.currentframe().f_code.co_name)
        try:
            return self.sync_api.items_archive.for_project(project_id).items()
        except ConnectionError as e:
            logger.error(f'Sync error. {e}')
            return []


class ProjectsManager(EntityManagerABC, TodoistApi):
    def __init__(self):
        EntityManagerABC.__init__(self, 'projects')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def full_sync(self):
        return self.rest_api.get_projects()

    def diff_sync(self):
        pass


class SectionsManager(EntityManagerABC, TodoistApi):
    def __init__(self):
        EntityManagerABC.__init__(self, 'sections')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def full_sync(self):
        return self.rest_api.get_sections()

    def diff_sync(self):
        pass


class LabelsManager(EntityManagerABC, TodoistApi):
    def __init__(self):
        EntityManagerABC.__init__(self, 'labels')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def full_sync(self):
        return self.rest_api.get_labels()

    def diff_sync(self):
        pass


class EventsManager(EntityManagerABC, TodoistApi):
    def __init__(self):
        EntityManagerABC.__init__(self, 'events')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def full_sync(self):
        return self._get_activity(page_limit=config.EVENTS_SYNC_FULL_SYNC_PAGES)

    def diff_sync(self):
        pass

    def _get_activity(self, page_limit=1, request_limit=100) -> List:
        logger.debug('Called' + inspect.currentframe().f_code.co_name + ', params: ' + str(locals()))

        # This is dumb! requests.get does not work! But curl does.
        # request_limit=100 is the max value for one page.
        events = []
        page = 0
        while page <= page_limit:
            offset_step = 0

            while True:
                activity = self._get_activity_page(request_limit, offset_step * request_limit, page)
                try:
                    events.extend(activity['events'])
                except KeyError:
                    logger.error(f'Failed to get events from activity: {activity}')

                max_offset_steps = activity['count'] // request_limit

                if max_offset_steps == offset_step:
                    break

                offset_step += 1

            page += 1

        return events

    @staticmethod
    def _get_last_event_for_object_by_type(events: List) -> Dict:
        # FixMe is this being used?

        events_sorted_by_date = sorted(events, key=itemgetter('event_date'), reverse=True)

        events_by_type = defaultdict(dict)
        seen = set()

        for event in events_sorted_by_date:
            event['is_completed'] = event['event_type'] == 'completed'
            event['is_deleted'] = event['event_type'] == 'deleted'
            if event['object_id'] not in seen:
                events_by_type[event['event_type']][event['object_id']] = event
                seen.add(event['object_id'])

        return events_by_type

    def _filter_new_events(self, events: List) -> List:

        last_event_datetime = self._get_last_known_event_dt()

        if last_event_datetime is None:
            return events

        res = []

        for i, event in events:
            event_datetime = datetime.strptime(event['event_date'], config.TODOIST_DATETIME_FORMAT)
            if event_datetime > last_event_datetime:
                res.append(event)

        return res

    def _save_events_to_db(self, events: List):
        pass

    def _get_activity_page(self, limit, offset, page):
        request = f'curl -s https://api.todoist.com/sync/{config.TODOIST_API_VERSION}/activity/get/ ' \
                  f'-H "Authorization: Bearer {self.token}" '
        request += f'-d page={page} -d limit={limit} -d offset={offset} '
        response = os.popen(request)
        return json.loads(response.read())

    @staticmethod
    def _get_last_known_event_dt():
        last_event_datetime_db = DBWorker.select('select event_datetime from events '
                                                 'order by event_datetime desc limit 1', fetch='one')
        if not last_event_datetime_db:
            return None

        return last_event_datetime_db[0]
