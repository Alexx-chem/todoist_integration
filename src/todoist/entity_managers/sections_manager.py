from .entity_manager_abc import EntityManagerABC


class SectionsManager(EntityManagerABC, TodoistApi):

    def __init__(self):
        EntityManagerABC.__init__(self, 'sections')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def _get_raw_items_from_api(self):
        return self.rest_api.get_sections()
