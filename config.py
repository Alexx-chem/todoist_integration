# Common
GLOBAL_LOG_LEVEL = 'INFO'

# Todoist connection
ALEXX_TODOIST_ID = '***REMOVED***'
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
           'cookie': '***REMOVED***'}
TODOIST_TOKEN = ''***REMOVED***''
TODOIST_API_VERSION = 'v9'

# TG config
BOT_TOKEN = ''***REMOVED***''
ALEXX_TG_CHAT_ID = '***REMOVED***'

# DB config
db_config = {'dbhost': 'localhost',
             'dbuser': 'postgres',
             'dbpass': '***REMOVED***',
             'dbname': 'consensus',
             'dbport': 5432}

# Todoist planner config

TODOIST_SYNC_TIMEOUT_SECONDS = 600

TODOIST_DATE_FORMAT = '%Y-%m-%d'

GOAL_LABEL_NAME = "Цель"
SUCCESS_LABEL_NAME = "Успех"


horizons = {
    'day': {'due_date': None},
    'week': {'due_date': None},
    'month': {'label': "Месяц"},
    'quarter': {'label': "Месяц"},
    'year': {'label': GOAL_LABEL_NAME,
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
