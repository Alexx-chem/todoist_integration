from typing import Callable, Iterable, List, Dict, Set
from collections import defaultdict
from operator import itemgetter
from datetime import datetime
import inspect
import json
import os

from db_worker import DBWorker

from src.todoist.api import TodoistApi
from src.logger import get_logger
from src.functions import set_db_timezone
from src.todoist.entity_manager_abc import EntityManagerABC
import config

logger = get_logger(__name__, 'console', config.GLOBAL_LOG_LEVEL)


class EntityManager(EntityManagerABC, TodoistApi):

    def __init__(self):
        super(TodoistApi).__init__(config.TODOIST_API_TOKEN)
        super(EntityManagerABC).__init__()

        for entity_type in config.ENTITY_TYPES:
            vars(self)[entity_type] = None

        set_db_timezone()

    def full_sync(self):
        pass

    def diff_sync(self):
        pass


class EventManager(EntityManagerABC):
    def __init__(self):
        super().__init__()

    def diff_sync(self, page_limit=1, request_limit=100) -> List:
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
        # TODO is it used?

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

    @staticmethod
    def _filter_new_events(events: List) -> List:

        last_event_datetime_db = DBWorker.select('select event_datetime from events '
                                                 'order by event_datetime desc limit 1', fetch='one')
        if not last_event_datetime_db:
            return events

        last_event_datetime = last_event_datetime_db[0]

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

class TaskManager(EntityManager):
    def __init__(self, api_token):
        super().__init__(api_token)


class ProjectManager(EntityManager):
    def __init__(self, api_token):
        super().__init__(api_token)
