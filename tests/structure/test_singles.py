import datetime

from nkssg.structure.singles import Singles, Single


def test_get_url_from_permalink_no_change():
    single = Single('', '')
    single.date = datetime.datetime.now()
    ret = single.get_url_from_permalink('/sample/', None)
    assert ret == '/sample/'


def test_get_url_from_permalink_YMD():
    single = Single('', '')
    now = datetime.datetime.now()
    single.date = datetime.datetime.now()
    ret = single.get_url_from_permalink('/%Y/%m/%d/', None)
    assert ret == now.strftime('/%Y/%m/%d/')
