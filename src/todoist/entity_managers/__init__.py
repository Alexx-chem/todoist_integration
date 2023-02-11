from .tasks_manager import TasksManager
from .projects_manager import ProjectsManager
from .sections_manager import SectionsManager
from .labels_manager import LabelsManager
from .events_manager import EventsManager
from .todoist_event import Event

ENTITY_TO_CLASS = {'tasks': TasksManager,
                   'projects': ProjectsManager,
                   'sections': SectionsManager,
                   'labels': LabelsManager,
                   'events': EventsManager}
