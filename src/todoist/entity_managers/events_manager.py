from typing import Iterable, List, Dict, Union
from datetime import datetime, timedelta
from collections import defaultdict
from operator import itemgetter
import json
import os

from db_worker import DBWorker

from .entity_manager_abc import EntityManagerABC
from src.functions import convert_dt
import config


class EventsManager(EntityManagerABC):

    def __init__(self):
        EntityManagerABC.__init__(self, 'events')

    def _load_items(self, *args, **kwargs):
        page_limit = self._get_pages(self._get_last_known_event_dt())
        super()._load_items(page_limit)

    def _get_raw_items_from_api(self, page_limit, request_limit=100) -> List:

        # This is dumb! requests.get does not work! But curl does.
        # request_limit=100 is the max value for one page.
        events = []
        page = 0
        while page <= page_limit:
            offset_step = 0

            while True:
                activity_page = self._get_activity_page(request_limit, offset_step * request_limit, page)
                try:
                    events.extend(activity_page['events'])
                except KeyError:
                    self.logger.error(f'Failed to get events from activity page object: {activity_page}')

                max_offset_steps = activity_page['count'] // request_limit

                if max_offset_steps == offset_step:
                    break

                offset_step += 1

            page += 1

        return events

    def get_filtered_new_items(self, items: List) -> List:

        last_event_dt = self._get_last_known_event_dt()

        if last_event_dt is None:
            return items

        res = []

        for event in items:
            if convert_dt(event['event_date']) > last_event_dt:
                res.append(event)

        return res

    def _process_update(self, items):
        pass

    def _save_events_to_db(self, events: List):
        pass

    def _get_activity_page(self, limit, offset, page):
        request = f'curl -s https://api.todoist.com/sync/{config.TODOIST_API_VERSION}/activity/get/ ' \
                  f'-H "Authorization: Bearer {self.token}" '
        request += f'-d page={page} -d limit={limit} -d offset={offset} '
        response = os.popen(request)
        return json.loads(response.read())

    @staticmethod
    def _get_last_known_event_dt() -> Union[datetime, None]:
        last_event_datetime_db = DBWorker.select('select event_datetime from events '
                                                 'order by event_datetime desc limit 1', fetch='one')
        if not last_event_datetime_db:
            return None

        return last_event_datetime_db[0]

    @staticmethod
    def _get_pages(last_event_dt: Union[datetime, None]) -> int:
        now = datetime.now()
        max_depth_dt = now - timedelta(weeks=config.EVENTS_SYNC_FULL_SYNC_PAGES)

        if last_event_dt is None or last_event_dt.date() < max_depth_dt:
            return config.EVENTS_SYNC_FULL_SYNC_PAGES

        return ((now - last_event_dt).days + 6) // 7

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

    @staticmethod
    def _get_events_by_type(events: List[Dict]) -> Dict:

        events_by_type = defaultdict(list)

        for event in events:
            events_by_type[event['event_type']].append(event)

        return events_by_type

    @property
    def current_by_type(self):
        return self._get_events_by_type(self._current_items)

    @property
    def synced_by_type(self):
        return self._get_events_by_type(self._synced_items)
