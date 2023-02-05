from typing import Iterable, List, Dict, Union


from .entity_manager import AbstractEntityManager


class ProjectsManager(AbstractEntityManager):

    _entity_name = 'projects'

    def __init__(self):
        AbstractEntityManager.__init__(self)

    def _get_items_from_api(self):
        return self.rest_api.get_projects()
