from abc import ABC, abstractmethod
import inspect


class EntityManagerABC(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def full_sync(self):
        """
        Entity Manager abstract method for full objects synchronization
        """

    @abstractmethod
    def diff_sync(self):
        """
        Entity Manager abstract method for objects update
        """
