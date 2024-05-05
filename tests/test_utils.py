import nkssg.utils as utils


def test_to_slug_no_change():
    dirty_slug = 'sample'
    ret = utils.to_slug(dirty_slug)
    assert ret == 'sample'


def test_to_slug_space():
    dirty_slug = 'a b c'
    ret = utils.to_slug(dirty_slug)
    assert ret == 'a-b-c'


def test_to_slug_upper():
    dirty_slug = 'Sample'
    ret = utils.to_slug(dirty_slug)
    assert ret == 'sample'


def test_to_slug_space_upper():
    dirty_slug = 'A of C'
    ret = utils.to_slug(dirty_slug)
    assert ret == 'a-of-c'
