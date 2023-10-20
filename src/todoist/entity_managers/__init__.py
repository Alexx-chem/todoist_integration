from todoist_api_python.models import Project, Section, Label

from src.todoist.entity_classes.todoist_event import Event
from src.todoist import ExtendedTask

ENTITY_CONFIG = {
    'tasks': {
        'entity_type': ExtendedTask,
        'attrs': {
            'assignee_id': {'col_type': 'varchar',
                            'constraints': ''},
            'assigner_id': {'col_type': 'varchar',
                            'constraints': ''},
            'comment_count': {'col_type': 'integer',
                              'constraints': ''},
            'is_completed': {'col_type': 'bool',
                             'constraints': 'NOT NULL DEFAULT false'},
            'content': {'col_type': 'varchar',
                        'constraints': 'NOT NULL'},
            'created_at': {'col_type': 'varchar',
                           'constraints': 'NOT NULL'},
            'creator_id': {'col_type': 'varchar',
                           'constraints': ''},
            'description': {'col_type': 'varchar',
                            'constraints': ''},
            'due.string': {'col_type': 'varchar',
                           'constraints': ''},
            'due.date': {'col_type': 'date',
                         'constraints': ''},
            'due.datetime': {'col_type': 'timestamp',
                             'constraints': ''},
            'due.is_recurring': {'col_type': 'bool',
                                 'constraints': 'NOT NULL DEFAULT false'},
            'due.timezone': {'col_type': 'varchar',
                             'constraints': ''},
            'id': {'col_type': 'varchar',
                   'constraints': 'NOT NULL'},
            'labels': {'col_type': 'varchar[]',
                       'constraints': ''},
            'order': {'col_type': 'integer',
                      'constraints': ''},
            'parent_id': {'col_type': 'varchar',
                          'constraints': ''},
            'priority': {'col_type': 'integer',
                         'constraints': 'NOT NULL'},
            'project_id': {'col_type': 'varchar',
                           'constraints': 'NOT NULL'},
            'section_id': {'col_type': 'varchar',
                           'constraints': ''},
            'url': {'col_type': 'varchar',
                    'constraints': 'NOT NULL'},
            'is_deleted': {'col_type': 'bool',
                           'constraints': 'NOT NULL DEFAULT false'},
            'is_goal': {'col_type': 'bool',
                        'constraints': 'NOT NULL DEFAULT false'},
            'is_active_goal': {'col_type': 'bool',
                               'constraints': 'NOT NULL DEFAULT false'},
            'is_active_with_due': {'col_type': 'bool',
                                   'constraints': 'NOT NULL DEFAULT false'},
            'is_active_no_due': {'col_type': 'bool',
                                 'constraints': 'NOT NULL DEFAULT false'},
            'is_active': {'col_type': 'bool',
                          'constraints': 'NOT NULL DEFAULT false'},
            'is_in_focus': {'col_type': 'bool',
                            'constraints': 'NOT NULL DEFAULT false'}
        },
        'pk': 'id'
    },
    'projects': {
        'entity_type': Project,
        'attrs': {
            'color': {'col_type': 'varchar',
                      'constraints': 'NOT NULL'},
            'comment_count': {'col_type': 'integer',
                              'constraints': ''},
            'id': {'col_type': 'varchar',
                   'constraints': 'NOT NULL'},
            'is_favorite': {'col_type': 'bool',
                            'constraints': 'NOT NULL DEFAULT false'},
            'is_inbox_project': {'col_type': 'bool',
                                 'constraints': 'NOT NULL DEFAULT false'},
            'is_shared': {'col_type': 'bool',
                          'constraints': 'NOT NULL DEFAULT false'},
            'is_team_inbox': {'col_type': 'bool',
                              'constraints': 'NOT NULL DEFAULT false'},
            'name': {'col_type': 'varchar',
                     'constraints': 'NOT NULL'},
            'order': {'col_type': 'integer',
                      'constraints': ''},
            'parent_id': {'col_type': 'varchar',
                          'constraints': ''},
            'url': {'col_type': 'varchar',
                    'constraints': 'NOT NULL'},
            'view_style': {'col_type': 'varchar',
                           'constraints': ''},
        }
    },
    'sections': {
        'entity_type': Section,
        'attrs': {
            'id': {'col_type': 'varchar',
                   'constraints': 'NOT NULL'},
            'name': {'col_type': 'varchar',
                     'constraints': 'NOT NULL'},
            'order': {'col_type': 'integer',
                      'constraints': ''},
            'project_id': {'col_type': 'varchar',
                           'constraints': 'NOT NULL'},
        }
    },
    'labels': {
        'entity_type': Label,
        'attrs': {
            'id': {'col_type': 'varchar',
                   'constraints': 'NOT NULL'},
            'name': {'col_type': 'varchar',
                     'constraints': 'NOT NULL'},
            'color': {'col_type': 'varchar',
                      'constraints': 'NOT NULL'},
            'order': {'col_type': 'integer',
                      'constraints': ''},
            'is_favorite': {'col_type': 'bool',
                            'constraints': 'NOT NULL DEFAULT false'}
        }
    },
    'events': {
        'entity_type': Event,
        'attrs': {
            'event_date': {'col_type': 'timestamp',
                           'constraints': ''},
            'event_type': {'col_type': 'varchar',
                           'constraints': 'NOT NULL'},
            'extra_data': {'col_type': 'varchar',
                           'constraints': ''},
            'id': {'col_type': 'varchar',
                   'constraints': 'NOT NULL'},
            'initiator_id': {'col_type': 'varchar',
                             'constraints': ''},
            'object_id': {'col_type': 'varchar',
                          'constraints': 'NOT NULL'},
            'object_type': {'col_type': 'varchar',
                            'constraints': 'NOT NULL'},
            'parent_item_id': {'col_type': 'varchar',
                               'constraints': ''},
            'parent_project_id': {'col_type': 'varchar',
                                  'constraints': ''},
        }
    }
}

from .tasks_manager import TasksManager
from .projects_manager import ProjectsManager
from .sections_manager import SectionsManager
from .labels_manager import LabelsManager
from .events_manager import EventsManager


def get_new_entity_managers():
    return {entity: _get_manager_by_entity_name(entity) for entity in ENTITY_CONFIG}


def _get_manager_by_entity_name(entity_name):

    assert entity_name in ENTITY_CONFIG.keys(), f'Unknown entity name: {entity_name}'

    if entity_name == 'tasks':
        return TasksManager
    if entity_name == 'projects':
        return ProjectsManager
    if entity_name == 'sections':
        return SectionsManager
    if entity_name == 'labels':
        return LabelsManager
    if entity_name == 'events':
        return EventsManager



