from .entity_manager import AbstractEntityManager


class LabelsManager(AbstractEntityManager, TodoistApi):

    def __init__(self):
        AbstractEntityManager.__init__(self, 'labels')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def _get_items_from_api(self, *args, **kwargs):
        return self.rest_api.get_labels()
