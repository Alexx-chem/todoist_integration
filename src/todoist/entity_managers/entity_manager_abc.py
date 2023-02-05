from typing import Iterable, List, Dict, Union, Set
from todoist_api_python.api import Task, Project, Section, Label
from abc import ABC, abstractmethod
import inspect

from db_worker import DBWorker

from src.functions import get_chained_attr, get_items_set_operation
from src.todoist.extended_task import ExtendedTask
from src.todoist.api import TodoistApi
from src.logger import get_logger

import config


class EntityManagerABC(ABC, TodoistApi):
    def __init__(self, entity_name):
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)
        self.logger = get_logger(self.__class__.__name__, 'console', config.GLOBAL_LOG_LEVEL)

        self._name = entity_name
        self._type = config.ENTITIES[self._name]['type']
        self._db_fields = config.ENTITIES[self._name]['db_fields']
        self._current_items = None
        self._synced_items = None

    def _load_items(self, *args, **kwargs):
        self.logger.debug(f'{inspect.currentframe().f_code.co_name} called')

        current_items = DBWorker.select(f'select * from {self._name}')
        self._current_items = self._objects_to_dict_by_id(current_items)

    def _sync_items(self, *args, **kwargs):
        self.logger.debug(f'{inspect.currentframe().f_code.co_name} called')

        synced_items = self._get_raw_items_from_api(*args, **kwargs)
        self._synced_items = self._objects_to_dict_by_id(synced_items)

    @abstractmethod
    def _get_raw_items_from_api(self, *args, **kwargs):
        """
        Entity Manager abstract method for objects synchronization
        """
        pass

    @abstractmethod
    def get_filtered_new_items(self, *args, **kwargs):
        """
        Entity Manager abstract method for filtering only new objects, absent in the DB
        """
        pass

    @staticmethod
    def _extend_tasks(tasks: Iterable[Task]) -> List[ExtendedTask]:
        return [ExtendedTask(task) for task in tasks]

    def _save_items_to_db(self, items,
                          sync_mode: str,
                          add_raw_data: bool = True):

        query = f'insert into {self._name} ({", ".join(self._db_fields)}{", raw_data" if add_raw_data else ""}) ' \
                f'SELECT {", ".join(["unnest(%(" + field_name + ")s)" for field_name in self._db_fields])} '
        if add_raw_data:
            if self._type == 'class':
                query += f", unnest({', '.join(item.__dict__ for item in items)}) "
            elif self._type == 'dict':
                query += f", unnest({', '.join(item for item in items)}) "

        values = self._prepare_values(items)

        if sync_mode == 'delete_all':
            DBWorker.input(f'delete from {self._name}')

        elif sync_mode == 'increment':
            query += f'where id not in (select id from {self._name})'

        DBWorker.input(query, data=values)

    def _prepare_values(self, items: List) -> Dict:

        if self._type == 'class':
            return dict(zip(self._db_fields,
                            zip(*((get_chained_attr(ent, k.split('.')) for k in self._db_fields)) for ent in items)))

        elif self._type == 'dict':
            return dict(zip(self._db_fields,
                            zip(*((d[k] for k in self._db_fields) for d in items))))

    @staticmethod
    def _objects_to_dict_by_id(lst: Iterable[Union[Task, Project, Section, Label, dict]]) -> Dict:
        if all((isinstance(obj, (Task, Project, Section, Label)) for obj in lst)):
            return {obj.id: obj for obj in lst}

        if all((isinstance(obj, dict) for obj in lst)):
            return {obj['id']: obj for obj in lst}

        raise ValueError(f'Wrong or non uniform types in the list: {set((type(obj) for obj in lst))}')

    @property
    def current_items(self) -> Dict:
        self._load_items()
        return self._current_items

    @property
    def synced_items(self) -> Dict:
        self._sync_items()
        return self._synced_items

    def _get_updated(self, mode: str = 'items'):

        assert mode in ('current', 'synced', 'diff'), f'Unknown mode value: {mode}'

        mode_converter = {'current': 'left',
                          'synced': 'right'}

        current = self.current_items
        synced = self.synced_items

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
    def updated_diff(self) -> Dict:
        return self._get_updated(mode='diff')

    @property
    def new(self) -> Dict:
        pass

    @property
    def removed(self) -> Dict:
        pass
