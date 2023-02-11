from typing import List, Dict, Union
from datetime import datetime, timedelta
from collections import defaultdict
from operator import itemgetter
import json
import os

from db_worker import DBWorker

from .entity_manager_abs import AbstractEntityManager, Event
import config


class EventsManager(AbstractEntityManager):

    _entity_name = 'events'
    _entity_type = Event

    def __init__(self):
        AbstractEntityManager.__init__(self)

    def sync_items(self, *args, **kwargs):
        page_limit = self._get_pages(self._get_last_known_event_dt())
        super().sync_items(page_limit)

    def load_items(self, *args, **kwargs):
        return super().load_items(*args, **kwargs)

    def _get_item_from_api(self, _id: str) -> Dict:
        return super()._get_item_from_api(_id=_id)

    def _get_items_from_api(self, page_limit: int, request_limit: int = 100) -> Dict:

        # This is dumb! requests.get does not work! But curl does.
        # request_limit=100 is the max value for one page.
        events_list = []
        page = 0
        while page <= page_limit:
            offset_step = 0

            while True:
                activity_page = self._get_activity_page(request_limit, offset_step * request_limit, page)
                try:
                    events_list.extend(activity_page['events'])
                except KeyError:
                    self.logger.error(f'Failed to get events from activity page object: {activity_page}')

                max_offset_steps = activity_page['count'] // request_limit

                if max_offset_steps == offset_step:
                    break

                offset_step += 1

            page += 1

        return self._to_dict_by_id(self.__items_dict_to_obj(events_list))

    def _get_activity_page(self, limit: int, offset: int, page: int) -> Dict:
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
    def _get_last_event_for_object_by_type(events: Dict[str, Event]) -> Dict:
        events_sorted_by_date = dict(sorted(events.items(), key=lambda item: item[1].event_date))

        events_by_type = defaultdict(dict)
        seen = set()

        for event in events_sorted_by_date.values():
            if event.object_id not in seen:
                events_by_type[event.event_type][event.object_id] = event
                seen.add(event.object_id)

        return events_by_type

    @staticmethod
    def _get_events_by_type(events: Dict[str, Event]) -> Dict:

        events_by_type = defaultdict(dict)

        for event_id, event in events.items():
            events_by_type[event.event_type][event_id] = event

        return events_by_type

    @property
    def current_by_type(self) -> Dict:
        return self._get_events_by_type(self._current_items)

    @property
    def synced_by_type(self) -> Dict:
        return self._get_events_by_type(self._synced_items)

    @property
    def current_last_for_item_by_date(self) -> Dict:
        return self._get_last_event_for_object_by_type(self._current_items)

    @property
    def synced_last_for_item_by_date(self) -> Dict:
        return self._get_last_event_for_object_by_type(self._synced_items)

    @property
    def new_by_type(self) -> Dict:
        return self._get_events_by_type(self.new)
