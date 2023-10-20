from datetime import datetime
from src.functions import get_today, unpack_chained_attr


def test_get_today():
    assert get_today().year == datetime.now().year
    assert get_today().month == datetime.now().month
    assert get_today().day == datetime.now().day


def test_unpack_chained_attr():
    class TestObj:

        def __init__(self):
            self.root = None

        def prepare(self):
            self.root = TestObj()
            self.root.a = 666

    test_obj = TestObj()
    test_obj.prepare()

    res = unpack_chained_attr(test_obj, ['root', 'a'])

    assert res == 666
