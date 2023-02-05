from .entity_manager import AbstractEntityManager


class SectionsManager(AbstractEntityManager, TodoistApi):

    def __init__(self):
        AbstractEntityManager.__init__(self, 'sections')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def _get_items_from_api(self):
        return self.rest_api.get_sections()
