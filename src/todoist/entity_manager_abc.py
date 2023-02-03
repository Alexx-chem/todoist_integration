from abc import ABC, abstractmethod
from typing import Iterable, List
from todoist_api_python.api import Task
import inspect

from src.todoist.extended_task import ExtendedTask


class EntityManagerABC(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def full_sync(self, *args, **kwargs):
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
