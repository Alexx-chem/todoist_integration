from datetime import datetime, date, timedelta
from typing import Union, Dict, List
from threading import Thread
from psycopg2.extras import Json
import traceback
import requests
import json

import config

from db_worker import DBWorker

DBWorker.set_config(config.DB_CONFIG)


def threaded(fn):
    def wrapper(*args, **kwargs):
        Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper


def custom_exception_handler(func, *args, verbose=True, **kwargs):
    try:
        res = func(*args, **kwargs)
        return res
    except Exception as e:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'{now}. Словили исключение {e}. Стек:')
        if verbose:
            print(traceback.format_exc())
            print('Едем дальше!')


def get_today():

    return datetime.now().date()


def get_end_of_the_week():
    today = get_today()

    return today + timedelta(days=6 - today.weekday())


def get_end_of_the_month(month: int = 0) -> date:
    assert 0 <= month <= 12

    today = get_today()
    month = month if month > 0 else today.month
    year = today.year
    next_month = date(day=1, month=month, year=year) + timedelta(days=31)

    return next_month - timedelta(days=next_month.day)


def get_end_of_the_quarter():
    last_quarter_month = ((get_today().month - 1) // 3 + 1) * 3

    return get_end_of_the_month(last_quarter_month)


def get_end_of_the_year():

    return datetime(day=31, month=12, year=get_today().year)


horizon_to_date = {
    'day': get_today,
    'week': get_end_of_the_week,
    'month': get_end_of_the_month,
    'quarter': get_end_of_the_quarter,
    'year': get_end_of_the_year
}


def set_db_timezone(utcoffset: str = None):

    if utcoffset is None:
        utcoffset = datetime.now().astimezone().tzinfo.utcoffset(None).seconds // 3600

    DBWorker.input(f"SET timezone TO {utcoffset}")


def unpack_chained_attr(obj, attr_chain):

    if not attr_chain or obj is None:
        return obj

    obj = getattr(obj, attr_chain.pop(0))

    return unpack_chained_attr(obj, attr_chain)


def convert_dt(dt: Union[datetime, date, str], str_type='datetime'):
    if isinstance(dt, datetime):
        return dt.strftime(config.TODOIST_DATETIME_FORMAT)

    if isinstance(dt, date):
        return dt.strftime(config.TODOIST_DATE_FORMAT)

    if isinstance(dt, str):
        if str_type == 'datetime':
            return datetime.strptime(dt, config.TODOIST_DATETIME_FORMAT)

        if str_type == 'date':
            return datetime.strptime(dt, config.TODOIST_DATE_FORMAT)


def get_items_set_operation(left: Dict, right: Dict, op: str) -> Dict:
    assert op in ('intersection', 'difference'), f'Unknown op value: {op}'

    res = {}

    if op == 'intersection':
        ids_subset = left.keys() & right.keys()
        res = {_id: {'left': left.get(_id),
                     'right': right.get(_id)} for _id in ids_subset}

    if op == 'difference':
        ids_subset = left.keys() - right.keys()
        res = {_id: left.get(_id) for _id in ids_subset}

    return res


def send_message_via_bot(text, delete_previous=False, save_msg_to_db=True):
    request = 'http://127.0.0.1:5000/send_message/'
    request += f'?chat_id={config.ALEXX_TG_CHAT_ID}'
    request += f'&text={text}'
    request += f'&delete_previous=true' if delete_previous else ''
    request += f'&save_msg_to_db=true' if save_msg_to_db else ''

    return requests.post(request)


def save_items_to_db(entity: str,
                     attrs: Dict,
                     items: Dict,
                     save_mode: str):

    assert save_mode in ('delete_all', 'increment', 'update'), f'Unknown save_mode: {save_mode}'

    if save_mode in ('delete_all', 'increment'):
        _insert_items_to_db(entity=entity,
                            attrs=attrs,
                            items=items,
                            save_mode=save_mode)

    elif save_mode == 'update':
        _update_items_in_db(entity=entity,
                            attrs=attrs,
                            items=items)


def _insert_items_to_db(entity: str,
                        attrs: Dict,
                        items: Dict,
                        save_mode: str):

    attrs_joined = '", "'.join(attrs.keys())
    values_template = ','.join(['%s'] * len(items))

    query = f'INSERT INTO {entity} ("{attrs_joined}") VALUES {values_template}'

    if save_mode == 'increment':
        query += f' ON CONFLICT (id) DO NOTHING'

    if save_mode == 'delete_all':
        DBWorker.input(f'DELETE FROM {entity}')

    values = _prepare_values(attrs, items)

    DBWorker.input(query, data=values)


def _update_items_in_db(entity, attrs, items):
    attrs_joined = '"=%s, "'.join(attrs.keys()) + '"=%s'
    query = f'UPDATE {entity} SET "{attrs_joined} WHERE id='

    for item in items.values():
        # FIXME hack with indexing
        query += f"'{item.id}'"
        values = _prepare_values(attrs=attrs, items={item.id: item})[0]
        DBWorker.input(query, data=values)


def _prepare_values(attrs: Dict, items: Dict) -> List:

    return [tuple(convert_to_json_if_dict(unpack_chained_attr(obj, attr.split('.')))
                  for attr in attrs) for obj in items.values()]


def convert_to_json_if_dict(attr_value):

    if isinstance(attr_value, dict):
        attr_value = Json(attr_value, dumps=lambda x: json.dumps(x, ensure_ascii=False))

    return attr_value
