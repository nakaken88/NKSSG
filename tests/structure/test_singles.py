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


def test_get_url_from_permalink_YMD_HMS():
    single = Single('', '')
    now = datetime.datetime.now()
    single.date = datetime.datetime.now()
    ret = single.get_url_from_permalink('/%Y/%m/%d/%H%M%S/', None)
    assert ret == now.strftime('/%Y/%m/%d/%H%M%S/')


def test_get_url_from_permalink_slug():
    single = Single('', '')
    single.date = datetime.datetime.now()
    single.slug = 'sample'
    ret = single.get_url_from_permalink('/{slug}/', None)
    assert ret == '/sample/'


def test_get_url_from_permalink_filename():
    single = Single('', '')
    single.date = datetime.datetime.now()
    single.filename = 'sample'
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/sample/'


def test_get_url_from_permalink_filename_index():
    single = Single('', '')
    single.date = datetime.datetime.now()
    single.filename = 'index'
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/'

