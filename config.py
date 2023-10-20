import os

# Common
GLOBAL_LOG_LEVEL = 'DEBUG'

# Todoist connection
ALEXX_TODOIST_ID = '***REMOVED***'
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
    'cookie': '***REMOVED***'}
TODOIST_API_TOKEN = os.getenv('TODOIST_API_TOKEN')
TODOIST_API_VERSION = 'v9'

# TG config
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
ALEXX_TG_CHAT_ID = '***REMOVED***'

# DB config
DB_CONFIG = {'dbhost': os.getenv('DBHOST'),
             'dbuser': os.getenv('DBUSER'),
             'dbpass': os.getenv('DBPASS'),
             'dbname': os.getenv('DBNAME'),
             'dbport': os.getenv('DBPORT'),
             'cursor_factory': 'dict_cursor'}

# Todoist workflow config

TODOIST_SYNC_TIMEOUT = 600  # seconds

TODOIST_DATE_FORMAT = '%Y-%m-%d'
TODOIST_DATETIME_FORMATS = (
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%dT%H:%M:%S.%fZ'
)

EVENTS_SYNC_FULL_SYNC_PAGES = 52  # One year. One page represents one week according to API docs

SPECIAL_LABELS = {'GOAL': "Цель",
                  'SUCCESS': "Успех"}

PLAN_HORIZONS = {
    'day': {'due_date': None},
    'week': {'due_date': None},
    'month': {'label': SPECIAL_LABELS['GOAL'],
              'due_date': None},
    'quarter': {'label': SPECIAL_LABELS['GOAL'],
                'due_date': None},
    'year': {'label': SPECIAL_LABELS['GOAL'],
             'due_date': None}
}

ENTITY_NAMES_TO_EVENT_OBJECT_TYPES = {
    'tasks': 'item',
    'projects': 'project',
    'sections': 'section',
    'labels': 'label',
}

TODOIST_TASK_CONTENT_LEN_THRESHOLD = 50

PLANNER_TASK_STATUS_TRANSITIONS = {
    'added': ('planned',),
    'loaded': ('planned',),
    # if completed task is recurring  -- it will be accounted as completed, and rescheduled as modified one
    'completed': ('planned', 'postponed', 'deleted'),
    'planned': ('completed', 'postponed', 'deleted'),
    'postponed': ('planned', 'completed', 'deleted'),
    'completed_recurring': ('planned', 'completed', 'postponed', 'deleted')
}

PLANNER_REPORT_SECTIONS_MARKS = {
    'completed': '\U00002705',
    'not_completed': '\U0000274C',
    'postponed': '\U0001F4C6',
    'deleted': '\U0001F5D1',
    'overall_planned': '\U0001F4CB',
    'compl_ratio': '\U0001F4C8'
}

EVENT_TYPES = [
    'added',
    'updated',
    'deleted',
    'completed',
    'uncompleted',
    'archived',
    'unarchived',
    'shared',
    'left'
]
