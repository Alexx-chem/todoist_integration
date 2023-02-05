from typing import Iterable, List, Dict, Union


from .entity_manager_abc import EntityManagerABC


class ProjectsManager(EntityManagerABC):

    def __init__(self):
        EntityManagerABC.__init__(self, 'projects')

    def _get_raw_items_from_api(self):
        return self.rest_api.get_projects()
