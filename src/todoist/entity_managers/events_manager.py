from typing import Dict, Union, List
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os

from db_worker import DBWorker

from .base_entity_manager import BaseEntityManager
from src.todoist.entity_classes import Event
from . import ENTITY_CONFIG
import config


class EventsManager(BaseEntityManager):

    _entity_name = 'events'
    _entity_type = ENTITY_CONFIG[_entity_name]['entity_type']
    _attrs = ENTITY_CONFIG[_entity_name]['attrs']

    def __init__(self):
        BaseEntityManager.__init__(self)

    def _get_item_from_api(self, _id: str) -> Dict:
        return super()._get_item_from_api(_id=_id)

    def _get_items_from_api(self, request_limit: int = 100) -> Dict:

        # This is dumb! requests.get does not work! But curl does.
        # request_limit=100 is the max value for one page.

        last_known_event_dt = self._get_last_known_event_dt()
        page_limit = self._get_pages(last_known_event_dt)

        events_list_full = []
        page = 0
        while page <= page_limit:
            offset_step = 0

            while True:
                activity_page = self._get_activity_page(request_limit, offset_step * request_limit, page)
                events_list = activity_page['events']

                try:
                    events_list_full.extend(events_list)
                except KeyError:
                    self.logger.error(f'Failed to get events from activity page object: {activity_page}')

                max_offset_steps = activity_page['count'] // request_limit
                oldest_offset_event_dt = datetime.strptime(events_list_full[-1]['event_date'],
                                                           config.TODOIST_DATETIME_FORMAT)
                if max_offset_steps == offset_step or oldest_offset_event_dt <= last_known_event_dt:
                    break

                offset_step += 1

            page += 1

        return self._to_dict_by_id(self._items_dict_to_obj(events_list_full))

    def _get_activity_page(self, limit: int, offset: int, page: int) -> Dict:
        request = f'curl -s https://api.todoist.com/sync/{config.TODOIST_API_VERSION}/activity/get/ ' \
                  f'-H "Authorization: Bearer {self.api.token}" '
        request += f'-d page={page} -d limit={limit} -d offset={offset} '
        response = os.popen(request)
        return json.loads(response.read())

    @staticmethod
    def _get_last_known_event_dt() -> Union[datetime, None]:
        last_event_datetime_db = DBWorker.select('select event_date from events '
                                                 'order by event_date desc limit 1', fetch='one')
        if not last_event_datetime_db:
            return datetime.now() - timedelta(weeks=config.EVENTS_SYNC_FULL_SYNC_PAGES)

        return last_event_datetime_db[0]

    @staticmethod
    def _get_pages(last_known_event_dt: Union[datetime, None]) -> int:
        now = datetime.now()
        max_depth_dt = now - timedelta(weeks=config.EVENTS_SYNC_FULL_SYNC_PAGES)

        if last_known_event_dt is None or last_known_event_dt.date() < max_depth_dt.date():
            return config.EVENTS_SYNC_FULL_SYNC_PAGES

        return ((now - last_known_event_dt).days + 6) // 7

    @staticmethod
    def _sort_events_by_date(events: Dict) -> Dict:
        return dict(sorted(events.items(), key=lambda item: item[1].event_date, reverse=True))

    def _get_last_event_for_object_by_event_type(self, events: Dict[str, Event],
                                                 entity_types: Union[List[str], None] = None) -> Dict:
        assert entity_types is None or isinstance(entity_types, list), f"Wrong entity_types: {type(entity_types)}"

        events_sorted_by_date = self._sort_events_by_date(events)

        events_by_type = defaultdict(dict)
        seen = {}
        for event in events_sorted_by_date.values():
            if entity_types is None or event.object_type in entity_types:
                if event.object_id not in seen:
                    events_by_type[event.event_type][event.object_id] = event
                    seen[event.object_id] = event.event_type

                elif event.event_type == 'added':
                    first_seen_status = seen[event.object_id]
                    if first_seen_status == 'deleted':
                        events_by_type[first_seen_status].pop(event.object_id)
                    elif first_seen_status != 'completed':
                        events_by_type[first_seen_status].pop(event.object_id)
                        events_by_type[event.event_type][event.object_id] = event

        return events_by_type

    @staticmethod
    def _get_events_by_criteria(events: Dict[str, Event], criteria: str) -> Dict:

        res = defaultdict(dict)

        for event_id, event in events.items():
            res[event.__dict__[criteria]][event_id] = event

        return res

    def _get_events_by_event_type(self, events: Dict[str, Event]) -> Dict:
        return self._get_events_by_criteria(events, 'event_type')

    def _get_events_by_object_type(self, events: Dict[str, Event]) -> Dict:
        return self._get_events_by_criteria(events, 'object_type')

    def _get_events_by_object_id(self, events: Dict[str, Event]) -> Dict:
        return self._get_events_by_criteria(events, 'object_id')

    @property
    def current_last_for_item_by_date(self) -> Dict:
        return self._get_last_event_for_object_by_event_type(self._current_items)

    @property
    def synced_last_for_item_by_date(self) -> Dict:
        return self._get_last_event_for_object_by_event_type(self._synced_items)

    @property
    def new_last_event_for_task_by_date(self) -> Dict:
        tasks_events_object_type = config.ENTITY_NAMES_TO_EVENT_OBJECT_TYPES['tasks']
        return self._get_last_event_for_object_by_event_type(self.new, entity_types=[tasks_events_object_type])

    def _new_events_for_object_type_by_object_id(self, entity_name):
        tasks_event_type = config.ENTITY_NAMES_TO_EVENT_OBJECT_TYPES[entity_name]
        new_tasks_events = self._get_events_by_object_type(self.new)[tasks_event_type]
        return self._get_events_by_object_id(new_tasks_events)

    @property
    def new_events_for_tasks_by_id(self):
        return self._new_events_for_object_type_by_object_id('tasks')

    @property
    def new_last_for_item_by_date(self) -> Dict:
        return self._get_last_event_for_object_by_event_type(self.new)

    def current_by_object_id(self, object_id: str) -> List:
        return [event for event in self.current.values() if event.object_id == object_id]

    def synced_by_object_id(self, object_id: str) -> List:
        return [event for event in self.synced.values() if event.object_id == object_id]
