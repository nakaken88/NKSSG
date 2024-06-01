import datetime

from nkssg.config import Config
from nkssg.structure.singles import Single


def test_get_url_from_permalink_no_change():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'sample.md'
    single = Single(dummy_path, config)
    ret = single.get_url_from_permalink('/sample/', None)
    assert ret == '/sample/'


def test_get_url_from_permalink_YMD():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'sample.md'
    single = Single(dummy_path, config)
    now = datetime.datetime.now()
    single.date = datetime.datetime.now()
    ret = single.get_url_from_permalink('/%Y/%m/%d/', None)
    assert ret == now.strftime('/%Y/%m/%d/')


def test_get_url_from_permalink_YMD_HMS():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'sample.md'
    single = Single(dummy_path, config)
    now = datetime.datetime.now()
    single.date = datetime.datetime.now()
    ret = single.get_url_from_permalink('/%Y/%m/%d/%H%M%S/', None)
    assert ret == now.strftime('/%Y/%m/%d/%H%M%S/')


def test_get_url_from_permalink_slug():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'sample.md'
    single = Single(dummy_path, config)
    single.slug = 'sample'
    ret = single.get_url_from_permalink('/{slug}/', None)
    assert ret == '/sample/'


def test_get_url_from_permalink_filename():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'sample.md'
    single = Single(dummy_path, config)
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/sample/'


def test_get_url_from_permalink_filename_dirty_name():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'A of C.md'
    single = Single(dummy_path, config)
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == r'/a%20of%20c/'


def test_get_url_from_permalink_filename_index():
    config = Config()
    config.update({'post_type': {'sample': {}}})
    dummy_path = config.docs_dir / 'sample' / 'dir1' / 'dir2' / 'index.md'
    single = Single(dummy_path, config)
    ret = single.get_url_from_permalink('/{filename}/', None)
    assert ret == '/dir2/'


def test_get_url_from_permalink_filename_top_index():
    config = Config()
    config.update({'post_type': {'sample': {'slug': 'new_post_type'}}})
    dummy_path = config.docs_dir / 'sample' / 'index.md'
    single = Single(dummy_path, config)
    ret = single.get_url_from_permalink('/{filename}/', 'new_post_type')
    assert ret == '/new_post_type/'
