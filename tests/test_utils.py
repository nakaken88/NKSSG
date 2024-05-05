import nkssg.utils as utils


def test_get_config_by_list_str_bool():
    config = {'x': True}
    ret = utils.get_config_by_list(config, 'x')
    assert ret is True


def test_get_config_by_list_str_value():
    config = {'x': 'X'}
    ret = utils.get_config_by_list(config, 'x')
    assert ret == 'X'


def test_get_config_by_list_str_none():
    config = {'x': 'X'}
    ret = utils.get_config_by_list(config, 'y')
    assert ret is None


def test_get_config_by_list_one_key_list():
    config = {'x': ['X', 'Y', 'Z']}
    ret = utils.get_config_by_list(config, ['x'])

    assert ret == ['X', 'Y', 'Z']


def test_get_config_by_list_two_keys_list():
    config = {'x': ['X', 'Y', 'Z']}
    ret = utils.get_config_by_list(config, ['x', 'X'])
    assert ret is None


def test_get_config_by_list_two_keys_dict():
    config = {'x': {'y': 'Y'}}
    ret = utils.get_config_by_list(config, ['x', 'y'])
    assert ret == 'Y'


def test_get_config_by_list_two_keys_list_dict():
    config = {'x': [{'x1': 'X1'}, {'y1': 'Y1'}, {'z1': 'Z1'}]}
    ret = utils.get_config_by_list(config, ['x', 'y1'])
    assert ret == 'Y1'


def test_get_config_by_list_three_keys_list():
    config = {'x': [{'x1': {'x11': 'X11'}}]}
    ret = utils.get_config_by_list(config, ['x', 'x1', 'x11'])
    assert ret == 'X11'


def test_get_config_by_list_three_keys_dict():
    config = {'x': {'y': {'z': 'Z'}}}
    ret = utils.get_config_by_list(config, ['x', 'y', 'z'])
    assert ret == 'Z'


def test_get_config_by_list_three_keys_no_data():
    config = {'x': {'y': {'z': 'Z'}}}
    ret = utils.get_config_by_list(config, ['X', 'Y', 'Z'])
    assert ret is None


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
