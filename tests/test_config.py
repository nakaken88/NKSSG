import nkssg.config as cfg


def test_default_config_no_content():
    config = {}
    config = cfg.set_default_config(config)

    assert config['site']['site_url'] == ''
    assert config['plugins'] == ['autop', 'awesome-page-link', 'awesome-img-link', 'select-pages']

    assert 'md' in config['doc_ext']
    assert config['post_type'][0]['post']['permalink'] == '/%Y/%m/%d/%H%M%S/'

    assert config['taxonomy'] == {}
    assert config['use_abs_url'] is True


def test_default_config_some_content():
    config = {
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
    config = cfg.set_default_config(config)

    assert config['site']['site_url'] == 'http://example.com'
    assert 'autop' in config['plugins']
    assert 'select-pages' not in config['plugins']

    assert 'md' not in config['doc_ext']
    assert config['post_type'][0]['post']['permalink'] == '/%Y/%m/%d/'

    assert config['taxonomy'] == ['category']
    assert config['use_abs_url'] is False
