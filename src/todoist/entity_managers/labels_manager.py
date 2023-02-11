from typing import Dict

from .entity_manager_abs import AbstractEntityManager, Label


class LabelsManager(AbstractEntityManager):

    _entity_name = 'labels'
    _entity_type = Label

    def __init__(self):
        AbstractEntityManager.__init__(self)

    def load_items(self, *args, **kwargs):
        return super().load_items(*args, **kwargs)

    def _get_item_from_api(self, _id: str) -> Dict:
        return super()._get_item_from_api(_id=_id)

    def _get_items_from_api(self, *args, **kwargs):
        return self.rest_api.get_labels()
