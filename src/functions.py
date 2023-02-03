from datetime import datetime, date, timedelta
from threading import Thread
import traceback

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
