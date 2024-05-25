from ruamel.yaml import YAML

from nkssg.config import Config


def test_default_config():
    config = Config()

    assert config['site']['site_name'] == 'Site Title'
    assert config.site.site_name == 'Site Title'
    assert config.site.site_url == ''
    assert config.plugins.get('select-pages') == {}

    assert 'md' in config.doc_ext

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


def test_taxonomy_config():
    yaml_text = """
taxonomy:
  tag:
    label: Tag
    term:
      - tag1
      - name: tag2
        slug: tag_two
      - tag3

  category:
    label: Category
    term:
      - cat1
      - name: cat11
        parent: cat1
      - name: cat12
        parent: cat1
      - cat2
"""

    config = Config()
    yaml = YAML(typ='safe')
    config.update(yaml.load(yaml_text))

    assert config.taxonomy['tag'].terms['tag2'].name == 'tag2'
    assert config.taxonomy['tag'].terms['tag3'].name == 'tag3'
    assert config.taxonomy['tag'].label == 'Tag'
    assert config.taxonomy['category'].terms['cat11'].parent == 'cat1'
