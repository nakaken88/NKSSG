from nkssg.config import Config, BaseConfig


def test_default_config_no_content():
    config = Config()

    assert config['site']['site_url'] == ''
    assert config['plugins'] == ['autop', 'awesome-page-link', 'awesome-img-link', 'select-pages']

    assert 'md' in config['doc_ext']
    assert config['post_type'][0]['post']['permalink'] == '/%Y/%m/%d/%H%M%S/'

    assert config['taxonomy'] == {}
    assert config['use_abs_url'] is True


def test_default_config_some_content():
    config = Config()
    config_dict = {
        'site': {
            'site_url': 'http://example.com'
        },
        'plugins': ['autop'],
        'doc_ext': ['html'],
        'post_type': [
            {
                'post': {
                    'permalink': '/%Y/%m/%d/'
                }
            }
        ],
        'taxonomy': ['category'],
        'use_abs_url': False
    }
    for k, v in config_dict.items():
        config[k] = v
        if k in config.__dict__:
            if isinstance(config.__dict__[k], BaseConfig):
                config.__dict__[k].update(v)
            else:
                config.__dict__[k] = v
        else:
            config.__dict__[k] = v

    assert config['site']['site_url'] == 'http://example.com'
    assert 'autop' in config['plugins']
    assert 'select-pages' not in config['plugins']

    assert 'md' not in config['doc_ext']
    assert config['post_type'][0]['post']['permalink'] == '/%Y/%m/%d/'

    assert config['taxonomy'] == ['category']
    assert config['use_abs_url'] is False
