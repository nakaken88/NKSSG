import datetime
from pathlib import Path

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


def test_get_url_from_permalink_filename_dirty_name():
    single = Single('', '')
    single.date = datetime.datetime.now()
    single.filename = 'A of C'
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/a-of-c/'


def test_get_url_from_permalink_filename_index():
    single = Single('', '')
    single.date = datetime.datetime.now()
    single.filename = 'index'
    single.src_dir = Path('post_type', 'dir1', 'dir2')
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/dir2/'


def test_get_url_from_permalink_filename_top_index():
    single = Single('', '')
    single.date = datetime.datetime.now()
    single.filename = 'index'
    single.src_dir = Path('post_type')
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/post_type/'

