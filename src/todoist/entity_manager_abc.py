from abc import ABC, abstractmethod
from typing import Iterable, List, Dict
from todoist_api_python.api import Task

from db_worker import DBWorker

from src.todoist.extended_task import ExtendedTask
from src.functions import get_chained_attr
from src.logger import get_logger
import config

logger = get_logger(__name__, 'console', config.GLOBAL_LOG_LEVEL)


class EntityManagerABC(ABC):
    def __init__(self, entity_name):
        self._name = entity_name
        self._type = config.ENTITIES[self._name]['type']
        self._db_fields = config.ENTITIES[self._name]['db_fields']
        self._items_from_api = None

    @abstractmethod
    def full_sync(self, *args, **kwargs):
        logger.debug(f'{self._name}: full_sync')
        self._items_from_api = self._get_items_from_api()
        self._save_items_to_db(db_save_mode=kwargs.get('db_save_mode', 'soft'))
        """
        Entity Manager abstract method for full objects synchronization
        """

    @abstractmethod
    def diff_sync(self, *args, **kwargs):
        """
        Entity Manager abstract method for objects update
        """

    @staticmethod
    def _objects_to_dict_by_id(lst: Iterable):
        return {obj.id: obj for obj in lst}

    @staticmethod
    def _extend_tasks(tasks: Iterable[Task]) -> List[ExtendedTask]:
        return [ExtendedTask(task) for task in tasks]

    def _save_items_to_db(self,
                          db_save_mode: str,
                          add_raw_data: bool = True):

        query = f'insert into {self._name} ({", ".join(self._db_fields)}{", raw_data" if add_raw_data else ""}) ' \
                f'SELECT {", ".join(["unnest(%(" + field_name + ")s)" for field_name in self._db_fields])} '
        if add_raw_data:
            if self._type == 'class':
                query += f", unnest({', '.join(item.__dict__ for item in self._items_from_api)}) "
            elif self._type == 'dict':
                query += f", unnest({', '.join(item for item in self._items_from_api)}) "

        values = self._prepare_values()

        if db_save_mode == 'hard':
            DBWorker.input(f'delete from {self._name}')

        elif db_save_mode == 'soft':
            query += f'where id not in (select id from {self._name})'

        DBWorker.input(query, data=values)

    def _prepare_values(self) -> Dict:

        if self._type == 'class':
            return dict(zip(self._db_fields,
                            zip(*((get_chained_attr(ent, k.split('.')) for k in self._db_fields))
                                for ent in self._items_from_api)))

        elif self._type == 'dict':
            return dict(zip(self._db_fields,
                            zip(*((d[k] for k in self._db_fields) for d in self._items_from_api))))
