import pytest
from ruamel.yaml import YAML

from nkssg.structure.config import Config


@pytest.fixture
def config():
    return Config()


def test_default_config(config):
    assert config['site']['site_name'] == 'Site Title'
    assert config.site.site_name == 'Site Title'
    assert config.site.site_url == ''
    assert config.plugins.get('select-pages') == {}

    assert 'md' in config.doc_ext

    assert config.taxonomy == {}
    assert config.use_abs_url is True


def test_site_config(config):
    config_dict = {
        'site': {
            'site_name': 'example site',
            'site_url': 'http://example.com',
        },
    }

    config.update(config_dict)

    assert config.site.site_name == 'example site'
    assert config.site.site_url == 'http://example.com'


def test_post_type_config(config):
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

    config.update(config_dict)

    assert config.post_type['post'].permalink == '/%Y/%m/%d/'
    assert config.post_type['sample'].archive_type == 'none'
    assert config.post_type['sample'].permalink == '/{slug}/'


def test_markdown_config(config):
    config_dict = {
        'markdown': {
            'fenced_code': {},
            'tables': {},
            'toc': {
                'marker': '[toc]',
            }
        },
    }

    config.update(config_dict)

    assert config.markdown['fenced_code'] == {}
    assert config.markdown['tables'] == {}
    assert config.markdown['toc']['marker'] == '[toc]'


def test_taxonomy_tag_config(config):
    yaml_text = """
taxonomy:
  tag:
    label: Tag
    term:
      - tag1
      - name: tag2
        slug: tag_two
      - tag3
"""

    yaml = YAML(typ='safe')
    config.update(yaml.load(yaml_text))

    assert config.taxonomy['tag'].label == 'Tag'
    assert config.taxonomy['tag'].terms['tag1'].name == 'tag1'
    assert config.taxonomy['tag'].terms['tag2'].name == 'tag2'
    assert config.taxonomy['tag'].terms['tag2'].slug == 'tag_two'


def test_taxonomy_category_config(config):
    yaml_text = """
taxonomy:
  category:
    label: Category
    term:
      - cat1
      - name: cat11
        parent: cat1
      - name: cat111
        parent: cat11
      - name: cat2
        term:
          - name: cat21
            term:
              - name: cat211
          - name: cat21
            slug: cat_two_one
      - name: cat31
        parent: cat3
      - name: cat3
"""

    yaml = YAML(typ='safe')
    config.update(yaml.load(yaml_text))

    assert config.taxonomy['category'].terms['cat1'].name == 'cat1'
    assert config.taxonomy['category'].terms['cat1'].parent == ''
    assert config.taxonomy['category'].terms['cat11'].parent == 'cat1'
    assert config.taxonomy['category'].terms['cat111'].parent == 'cat11'

    assert config.taxonomy['category'].terms['cat21'].parent == 'cat2'
    assert config.taxonomy['category'].terms['cat21'].slug == 'cat_two_one'
    assert config.taxonomy['category'].terms['cat211'].parent == 'cat21'

    assert config.taxonomy['category'].terms['cat31'].parent == 'cat3'
