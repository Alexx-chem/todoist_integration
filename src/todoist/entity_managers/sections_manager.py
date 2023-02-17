from typing import Dict

from .entity_manager_abs import BaseEntityManager
from . import ENTITY_CONFIG


class SectionsManager(BaseEntityManager):

    _entity_name = 'sections'
    _entity_type = ENTITY_CONFIG[_entity_name]['entity_type']
    _attrs = ENTITY_CONFIG[_entity_name]['attrs'].keys()

    def __init__(self):
        BaseEntityManager.__init__(self)

    def load_items(self, *args, **kwargs):
        return super().load_items(*args, **kwargs)

    def _get_item_from_api(self, _id: str) -> Dict:
        item = self.api.rest_api.get_section(section_id=_id)
        return {item.id: item}

    def _get_items_from_api(self, *args, **kwargs):
        return self._to_dict_by_id(self.api.rest_api.get_sections())
