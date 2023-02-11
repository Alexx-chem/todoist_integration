from todoist_api_python.models import Task, Project, Section, Label
from typing import Union

from src.todoist.entity_classes.todoist_event import Event
from src.todoist import ExtendedTask


ENTITY_CONFIG = {
    'tasks': {
        'manager_class_name': 'TasksManager',
        'entity_type': ExtendedTask,
        'attrs': {
            'assignee_id': 'varchar',
            'assigner_id': 'varchar',
            'comment_count': 'integer',
            'is_completed': 'bool NOT NULL DEFAULT false',
            'content': 'varchar NOT NULL',
            'created_at': 'varchar NOT NULL',
            'creator_id': 'varchar',
            'description': 'varchar',
            'due.string': 'varchar',
            'due.date': 'date',
            'due.datetime': 'timestamp',
            'due.is_recurring': 'bool',
            'due.timezone': 'varchar',
            'id': 'varchar not null',
            'labels': '_varchar',
            'order': 'integer',
            'parent_id': 'varchar',
            'priority': 'integer NOT NULL',
            'project_id': 'varchar NOT NULL',
            'section_id': 'varchar',
            'url': 'varchar NOT NULL',
            'is_deleted': 'bool NOT NULL DEFAULT false',
            'is_goal': 'bool NOT NULL DEFAULT false',
            'is_active_goal': 'bool NOT NULL DEFAULT false',
            'is_active_with_due': 'bool NOT NULL DEFAULT false',
            'is_active_no_due': 'bool NOT NULL DEFAULT false',
            'is_active': 'bool NOT NULL DEFAULT false',
            'is_in_focus': 'bool NOT NULL DEFAULT false'
        },
        'pk': 'id'
    },
    'projects': {
        'manager_class_name': 'ProjectsManager',
        'entity_type': Project,
        'attrs': {
            'color': 'varchar NOT NULL',
            'comment_count': 'integer',
            'id': 'varchar NOT NULL',
            'is_favorite': 'bool NOT NULL DEFAULT false',
            'is_inbox_project': 'bool NOT NULL DEFAULT false',
            'is_shared': 'bool NOT NULL DEFAULT false',
            'is_team_inbox': 'bool NOT NULL DEFAULT false',
            'name': 'varchar NOT NULL',
            'order': 'integer',
            'parent_id': 'varchar',
            'url': 'varchar NOT NULL',
            'view_style': 'varchar',
        }
    },
    'sections': {
        'manager_class_name': 'SectionsManager',
        'entity_type': Section,
        'attrs': {'id': 'varchar NOT NULL',
                  'name': 'varchar NOT NULL',
                  'order': 'integer',
                  'project_id': 'varchar NOT NULL'
                  }
    },
    'labels': {
        'manager_class_name': 'LabelsManager',
        'entity_type': Label,
        'attrs': {
            'id': 'varchar NOT NULL',
            'name': 'varchar NOT NULL',
            'color': 'varchar NOT NULL',
            'order': 'integer',
            'is_favorite': 'bool NOT NULL DEFAULT false'
        }
    },
    'events': {
        'manager_class_name': 'EventsManager',
        'entity_type': Event,
        'attrs': {
            'event_date': 'timestamp',
            'event_type': 'varchar NOT NULL',
            'extra_data': 'varchar',
            'id': 'varchar NOT NULL',
            'initiator_id': 'varchar',
            'object_id': 'varchar NOT NULL',
            'object_type': 'varchar NOT NULL',
            'parent_item_id': 'varchar',
            'parent_project_id': 'varchar'
        }
    }
}

ENTITY_ITEMS_TYPING = Union[Task, Project, Section, Label, Event]

from .tasks_manager import TasksManager
from .projects_manager import ProjectsManager
from .sections_manager import SectionsManager
from .labels_manager import LabelsManager
from .events_manager import EventsManager
