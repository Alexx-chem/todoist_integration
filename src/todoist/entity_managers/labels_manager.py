from .entity_manager_abc import EntityManagerABC


class LabelsManager(EntityManagerABC, TodoistApi):

    def __init__(self):
        EntityManagerABC.__init__(self, 'labels')
        TodoistApi.__init__(self, config.TODOIST_API_TOKEN)

    def _get_raw_items_from_api(self, *args, **kwargs):
        return self.rest_api.get_labels()
