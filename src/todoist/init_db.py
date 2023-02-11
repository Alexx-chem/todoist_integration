from .entity_managers import ENTITY_CONFIG
from db_worker import DBWorker

import config

DBWorker.set_config(config.DB_CONFIG)


def create_tables():
    for entity in ENTITY_CONFIG:
        attrs = ENTITY_CONFIG[entity]["attrs"]
        attrs_joined = ", ".join([" ".join((f'"{tab_name}"', props)) for tab_name, props in attrs.items()])
        query = f'CREATE table IF NOT EXISTS {entity} ({attrs_joined}'
        if 'id' not in attrs:
            query += ')'
        else:
            query += f', CONSTRAINT {entity}_pk PRIMARY KEY (id))'

        DBWorker.input(query)


if __name__ == '__main__':
    create_db()
    create_tables()
