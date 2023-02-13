from typing import Iterable, List, Dict, Union
from abc import ABC, abstractmethod
import inspect

from db_worker import DBWorker

from src.functions import get_items_set_operation
from src.todoist.api import TodoistApi
from src.logger import get_logger

import config


class AbstractEntityManager(ABC, TodoistApi):
    _entity_name = None
    _entity_type = None
    _attrs = None

    def __init__(self):
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)
        self.logger = get_logger(self.__class__.__name__, 'console', config.GLOBAL_LOG_LEVEL)

        self._current_items: Union[Dict, None] = None
        self._synced_items: Union[Dict, None] = None

        self.load_items()

    @abstractmethod
    def load_items(self, *args, **kwargs):
        self.logger.debug(f'{inspect.currentframe().f_code.co_name} called')

        self._current_items = self._get_items_from_db()

    def sync_items(self, *args, **kwargs):
        self.logger.debug(f'{inspect.currentframe().f_code.co_name} called')

        self._synced_items = self._get_items_from_api(*args, **kwargs)

    def load_item_by_id(self, item_id: str) -> Dict[str, _entity_type]:
        return self._get_item_from_db(item_id)

    def sync_item_by_id(self, item_id: str) -> Dict[str, _entity_type]:
        return self._get_item_from_api(item_id)

    @abstractmethod
    def _get_items_from_api(self, *args, **kwargs) -> Dict:
        """
        Entity Manager abstract method for objects synchronization
        """

    @abstractmethod
    def _get_item_from_api(self, _id: str) -> Dict:
        """
        Entity Manager abstract method for single object synchronization
        """

    def _get_items_from_db(self) -> Dict:
        joiner = '", "'
        items = DBWorker.select(f'select "{joiner.join(self._attrs)}" from {self._entity_name}')
        items_list = (self._entity_type.from_dict(dict(zip(self._attrs, row))) for row in items)
        return self._to_dict_by_id(items_list)

    def _get_item_from_db(self, _id: str) -> Dict:
        item = DBWorker.select(f"select {', '.join(self._attrs)} from {self._entity_name} where id = '{_id}'",
                               fetch='one')
        item_dict = {item[0]: item}
        return self._entity_type.from_dict(item_dict)

    @staticmethod
    def _to_dict_by_id(items: Iterable) -> Dict:
        return {obj.id: obj for obj in items}

    @property
    def current(self) -> Dict:
        return self._current_items

    @property
    def synced(self) -> Dict:
        return self._synced_items

    @property
    def updated_diff(self) -> Dict:
        return self._get_updated_items(mode='diff')

    @property
    def updated_current(self) -> Dict:
        return self._get_updated_items(mode='current')

    @property
    def updated_synced(self) -> Dict:
        return self._get_updated_items(mode='synced')

    def _get_updated_items(self, mode: str):

        assert mode in ('current', 'synced', 'diff'), f'Unknown mode value: {mode}'

        mode_converter = {'current': 'left',
                          'synced': 'right'}

        current = self.current
        synced = self.synced

        intersection = get_items_set_operation(left=current,
                                               right=synced,
                                               op='intersection')
        res = {}
        for _id in intersection:

            if mode in ('current', 'synced'):
                res[_id] = intersection[_id][mode_converter[mode]]
            elif mode == 'diff':
                res[_id] = {}
                for property_key in intersection[_id]:
                    current_value = current[_id][property_key]
                    synced_value = synced[_id][property_key]
                    if current_value != synced_value:
                        res[_id][property_key] = {'current': current_value,
                                                  'synced': synced_value}
        return res

    @property
    def new(self) -> Dict:
        return self._get_items_set_diff('synced')

    @property
    def removed(self) -> Dict:
        return self._get_items_set_diff('current')

    def _get_items_set_diff(self, mode: str):

        assert mode in ('current', 'synced'), f"Wrong mode: {mode}"

        current = self._current_items
        synced = self._synced_items

        if mode == 'current':
            return get_items_set_operation(left=current,
                                           right=synced,
                                           op=f'difference')
        if mode == 'synced':
            return get_items_set_operation(left=synced,
                                           right=current,
                                           op=f'difference')

    def get_current_item_by_id(self, item_id: str) -> _entity_type:
        return self._current_items[item_id]

    def get_synced_item_by_id(self, item_id: str) -> _entity_type:
        return self._synced_items[item_id]

    def _items_dict_to_obj(self, item_dict_list: List[Dict]) -> List:
        return [self._entity_type.from_dict(item) for item in item_dict_list]


class BaseEntityManager(AbstractEntityManager):
    # TODO!
    pass
