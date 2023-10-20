from typing import Dict

from src.functions import save_items_to_db
from .entity_managers import ENTITY_CONFIG
from db_worker import DBWorker


from src.logger import get_logger
import config

DBWorker.set_config(config.DB_CONFIG)

logger = get_logger(__name__, 'console', logging_level=config.GLOBAL_LOG_LEVEL)


CREATE_QUERIES = {'plans': 'CREATE TABLE public."plans" ('
                           'id int4 NOT NULL DEFAULT nextval(\'plan_id_seq\'::regclass), '
                           'horizon varchar NOT NULL, '
                           'start_date timestamp NOT NULL, '
                           'end_date timestamp NOT NULL, '
                           'active bool NOT NULL DEFAULT false'
                           ')',
                  'tasks_in_plans': 'CREATE TABLE public.tasks_in_plans ('
                                    'record_id serial4 NOT NULL, '
                                    'task_id varchar NOT NULL, '
                                    'plan_id int4 NOT NULL, '
                                    'status varchar NOT NULL, '
                                    '"timestamp" timestamp NOT NULL,'
                                    'CONSTRAINT tasks_in_plans_pk PRIMARY KEY (record_id)'
                                    ')',
                  'system_params': 'CREATE TABLE public.system_params ('
                                   'value varchar NOT NULL, '
                                   'param varchar NOT NULL UNI'
                                   ')'}


def create_tables():
    for entity in ENTITY_CONFIG:
        attrs = ENTITY_CONFIG[entity]["attrs"]
        attrs_joined = ", ".join([" ".join((f'"{tab_name}"',
                                            props['col_type'],
                                            props['constraints'])) for tab_name, props in attrs.items()])
        query = f'CREATE table IF NOT EXISTS {entity} ({attrs_joined}'
        if 'id' not in attrs:
            query += ')'
        else:
            query += f', CONSTRAINT {entity}_pk PRIMARY KEY (id))'

        DBWorker.input(query)

    for table_name in CREATE_QUERIES:
        DBWorker.input(CREATE_QUERIES[table_name])

    DBWorker.input("UPDATE TABLE system_params SET value = 'true' WHERE param = 'tables_created'")


def init_system_params():
    DBWorker.input("INSERT INTO system_params param VALUES ('tables_created'),"
                   "                                       ('initial_tables_fill_complete')")


def fill_item_tables_from_scratch(managers: Dict, check=True):
    logger.debug('Filling tables')
    if check:
        tables_filled = DBWorker.select("SELECT value FROM system_params WHERE param = 'initial_tables_fill_complete'",
                                        fetch='one')
        if tables_filled[0] == 'true':
            logger.debug('Tables already filled')
            return True

    for entity in ENTITY_CONFIG:
        manager_name = entity + "_manager"
        attrs = ENTITY_CONFIG[entity]["attrs"]

        managers[manager_name].sync_items()
        items = managers[manager_name].synced

        save_items_to_db(entity, attrs, items, save_mode='delete_all')

    DBWorker.input("UPDATE system_params SET value = 'true' WHERE param = 'initial_tables_fill_complete'")

    logger.debug('Tables filled!')

    return True


if __name__ == '__main__':
    create_tables()
