# Todoist connection
todo_alexx_id = '***REMOVED***'
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
           'cookie': '***REMOVED***'}
todoist_token = '0bb3211b3219a66ef40020857cbcc00f108cd8a7'

# TG config
bot_token = ''***REMOVED***''
alexx_chat_id = '***REMOVED***'

# DB config
db_config = {'dbhost': 'localhost',
             'dbuser': 'postgres',
             'dbpass': '***REMOVED***',
             'dbname': 'consensus',
             'dbport': 5432}

# Todoist planner config

todoist_date_format = '%Y-%m-%d'

goal_label_name = "Цель"
success_label_name = "Успех"


horizons = {
    'day': {'due_date': None},
    'week': {'due_date': None},
    'month': {'label': "Месяц"},
    'quarter': {'label': "Месяц"},
    'year': {'label': goal_label_name,
             'priority':  4}
}

task_actions = ['created',
                'modified',
                'completed',
                'deleted']

status_transitions = {
    'new': ('planned', ),
    'planned': ('postponed', 'completed', 'deleted'),
    'postponed': ('planned', ),
    'completed': ('planned', 'deleted'),
    'deleted': (None, )
}
