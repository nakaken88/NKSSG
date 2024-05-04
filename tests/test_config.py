from nkssg.config import Config


def test_default_config():
    config = Config()

    assert config['site']['site_name'] == 'Site Title'
    assert config.site.site_name == 'Site Title'
    assert config.site.site_url == ''
    assert config.plugins.get('select-pages') == {}

    assert 'md' in config.doc_ext
    assert config.post_type['post'].permalink == '/%Y/%m/%d/%H%M%S/'

    assert config.taxonomy == {}
    assert config.use_abs_url is True


def test_site_config():
    config_dict = {
        'site': {
            'site_name': 'example site',
            'site_url': 'http://example.com',
        },
    }

    config = Config()
    config.update(config_dict)

    assert config.site.site_name == 'example site'
    assert config.site.site_url == 'http://example.com'


def test_post_type_config():
    config_dict = {
        'post_type': {
            'post': {
                'permalink': '/%Y/%m/%d/',
            },
            'sample': {
                'archive_type': 'none',
            }
        },
    }

    config = Config()
    config.update(config_dict)

    assert config.post_type['post'].permalink == '/%Y/%m/%d/'
    assert config.post_type['sample'].archive_type == 'none'
    assert config.post_type['sample'].permalink == '/{slug}/'


def test_markdown_config():
    config_dict = {
        'markdown': {
            'fenced_code': {},
            'tables': {},
            'toc': {
                'marker': '[toc]',
            }
        },
    }

    config = Config()
    config.update(config_dict)

    assert config.markdown['fenced_code'] == {}
    assert config.markdown['tables'] == {}
    assert config.markdown['toc']['marker'] == '[toc]'
