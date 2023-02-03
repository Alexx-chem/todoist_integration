# Common
GLOBAL_LOG_LEVEL = 'DEBUG'

# Todoist connection
ALEXX_TODOIST_ID = '***REMOVED***'
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
           'cookie': '***REMOVED***'}
TODOIST_API_TOKEN = ''***REMOVED***''
TODOIST_API_VERSION = 'v9'

# TG config
TG_BOT_TOKEN = ''***REMOVED***''
ALEXX_TG_CHAT_ID = '***REMOVED***'

# DB config
DB_CONFIG = {'dbhost': 'localhost',
             'dbuser': 'postgres',
             'dbpass': '***REMOVED***',
             'dbname': 'todoist',
             'dbport': 5432}

# Todoist workflow config

TODOIST_SYNC_TIMEOUT = 600  # seconds

TODOIST_DATE_FORMAT = '%Y-%m-%d'
TODOIST_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S:%fZ'

EVENTS_SYNC_FULL_SYNC_PAGES = 52  # One year. One page represents one week according to API docs

SPECIAL_LABELS = {'GOAL_LABEL_NAME': "Цель",
                  'SUCCESS_LABEL_NAME': "Успех"}

ENTITIES = {'tasks': {'type': 'class',
                      'db_fields': ['id',
                                    'due.date',
                                    'due.datetime',
                                    'priority',
                                    'content',
                                    'project_id',
                                    'labels',
                                    'is_completed',
                                    'is_deleted',
                                    'is_recurring',
                                    'parent_id',
                                    'raw_data']},
            'projects': {'type': 'class',
                         'db_fields': ['id',
                                       'name',
                                       'parent_id',
                                       'is_inbox_project',
                                       'raw_data']},
            'sections': {'type': 'class',
                         'db_fields': ['id',
                                       'name',
                                       'project_id',
                                       'raw_data']},
            'labels': {'type': 'class',
                       'db_fields': ['id',
                                     'name',
                                     'raw_data']},
            'events': {'type': 'dict',
                       'db_fields': ['id',
                                     'object_type',
                                     'event_type',
                                     'object_id',
                                     'event_datetime',
                                     'raw_data']}
            }

PLAN_HORIZONS = {
    'day': {'due_date': None},
    'week': {'due_date': None},
    'month': {'label': "Месяц"},
    'quarter': {'label': "Месяц"},
    'year': {'label': SPECIAL_LABELS['GOAL_LABEL_NAME'],
             'priority':  4}
}

task_actions = ['created',
                'modified',
                'completed',
                'uncompleted',
                'deleted',
                'loaded']

status_transitions = {
    'new': ('planned', ),
    'planned': ('postponed', 'completed', 'deleted'),
    'postponed': ('planned', ),
    'completed': ('planned', 'deleted'),
    'deleted': (None, )
}

report_sections_marks = {'completed': '\U00002705',
                         'not_completed': '\U0000274C',
                         'postponed': '\U0001F4C6',
                         'deleted': '\U0001F5D1',
                         'overall_planned': '\U0001F4CB',
                         'compl_ratio': '\U0001F4C8'}
