from .tasks_manager import TasksManager
from .projects_manager import ProjectsManager
from .sections_manager import SectionsManager
from .labels_manager import LabelsManager
from .events_manager import EventsManager

import config


def get_manager(entity_name):
    assert entity_name in config.ENTITIES, f'Unknown entity name: {entity_name}'
    if entity_name == 'tasks':
        return TasksManager()
    if entity_name == 'projects':
        return ProjectsManager()
    if entity_name == 'sections':
        return SectionsManager()
    if entity_name == 'labels':
        return LabelsManager()
    if entity_name == 'events':
        return EventsManager()
