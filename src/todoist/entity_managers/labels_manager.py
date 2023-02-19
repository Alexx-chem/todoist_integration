from typing import Dict

from .base_entity_manager import BaseEntityManager
from . import ENTITY_CONFIG


class LabelsManager(BaseEntityManager):

    _entity_name = 'labels'
    _entity_type = ENTITY_CONFIG[_entity_name]['entity_type']
    _attrs = ENTITY_CONFIG[_entity_name]['attrs']

    def __init__(self):
        BaseEntityManager.__init__(self)

    def load_items(self, *args, **kwargs):
        return super().load_items(*args, **kwargs)

    def _get_item_from_api(self, _id: str) -> Dict:
        item = self.api.rest_api.get_label(label_id=_id)
        return {item.id: item}

    def _get_items_from_api(self, *args, **kwargs):
        return self._to_dict_by_id(self.api.rest_api.get_labels())
