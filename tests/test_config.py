import pytest
from ruamel.yaml import YAML
from pathlib import Path

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


def test_from_file_success(tmp_path: Path):
    """
    Tests that the config can be loaded correctly from a valid YAML file.
    """
    config_content = """
    site:
      site_name: 'Test Site'
    """
    config_file = tmp_path / "test.yml"
    config_file.write_text(config_content, encoding="utf-8")

    config = Config.from_file(yaml_file_path=config_file)

    assert config.site.site_name == 'Test Site'


def test_from_file_not_found():
    """
    Tests that a FileNotFoundError is raised if the file does not exist.
    """
    with pytest.raises(FileNotFoundError):
        Config.from_file(yaml_file_path=Path("non_existent_file.yml"))


def test_invalid_term_name_is_ignored(tmp_path: Path):
    """
    Tests that terms with empty or whitespace-only names are ignored.
    """
    config_content = """
    taxonomy:
      tag:
        term:
          - 'tag1'
          - '  '  # Whitespace-only term
          - 'tag2'
    """
    config_file = tmp_path / "test.yml"
    config_file.write_text(config_content, encoding="utf-8")

    config = Config.from_file(yaml_file_path=config_file)

    assert 'tag1' in config.taxonomy['tag'].terms
    assert 'tag2' in config.taxonomy['tag'].terms
    assert len(config.taxonomy['tag'].terms) == 2


def test_from_file_with_invalid_yaml(tmp_path: Path):
    """
    Tests that a ValueError is raised for malformed YAML.
    """
    config_content = "site: { site_name: 'Test Site }"
    config_file = tmp_path / "test.yml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match="The YAML format is incorrect: .*"):
        Config.from_file(yaml_file_path=config_file)


def test_term_missing_name_key_raises_error(tmp_path: Path):
    """
    Tests that a ValueError is raised if a term dict is missing the 'name' key.
    """
    config_content = """
    taxonomy:
      tag:
        term:
          - slug: 'a-slug-without-a-name'  # This entry is invalid
    """
    config_file = tmp_path / "test.yml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match=r"Term dictionary must have a 'name' key: .*"):
        Config.from_file(yaml_file_path=config_file)
