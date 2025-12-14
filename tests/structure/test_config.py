import pytest

from pathlib import Path

from nkssg.structure.config import Config, SiteConfig


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
            'site_url': 'http://example.com/',  # With trailing slash
            'site_image': 'http://example.com/images/hero.jpg',
        },
    }

    config.update(config_dict)

    assert config.site.site_name == 'example site'
    assert config.site.site_url == 'http://example.com'  # Assert that trailing slash is removed
    assert config.site.site_url_original == 'http://example.com/' # Assert that original URL is preserved
    assert config.site.site_image == '/images/hero.jpg'  # Assert that it becomes a relative path


def test_post_type_config(config):
    config_dict = {
        'post_type': {
            'post': {
                'permalink': '/%Y/%m/%d/',
            },
            'sample': {
                'archive_type': 'none',
            },
            'page': {
                'archive_type': 'invalid_type',  # Set an invalid value
            }
        },
    }

    config.update(config_dict)

    assert config.post_type['post'].permalink == '/%Y/%m/%d/'
    assert config.post_type['sample'].archive_type == 'none'
    assert config.post_type['sample'].permalink == '/{slug}/'
    assert config.post_type['page'].archive_type == 'section'  # Assert that it falls back to 'section'



def test_directory_paths_config(config):
    config_dict = {
        'directory': {
            'docs': 'my_docs_path',
            'public': 'my_public_path',
        },
    }

    original_base_dir = config.base_dir  # base_dir is initialized with Path.cwd()

    config.update(config_dict)

    assert config.docs_dir == original_base_dir / 'my_docs_path'
    assert config.public_dir == original_base_dir / 'my_public_path'
    # Assert that other default directories remain unchanged
    assert config.static_dir == original_base_dir / 'static'
    assert config.themes_dir == original_base_dir / 'themes'



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
    config._update_from_yaml_string(yaml_text)

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

    config._update_from_yaml_string(yaml_text)

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


def test_mode_handling(tmp_path: Path):
    """
    Tests that the 'mode' is correctly handled by both the constructor and from_file.
    """
    config_default = Config()
    assert config_default.mode == 'build'

    config_serve = Config(mode='serve')
    assert config_serve.mode == 'serve'

    config_with_data = Config(mode='draft')
    config_with_data.update({'site': {'site_name': 'Test'}})
    assert config_with_data.mode == 'draft'
    assert config_with_data.site.site_name == 'Test'

    (tmp_path / "empty.yml").touch()
    config_from_file_default = Config.from_file(yaml_file_path=tmp_path / "empty.yml")
    assert config_from_file_default.mode == 'build'

    config_from_file_serve = Config.from_file(yaml_file_path=tmp_path / "empty.yml", mode='serve')
    assert config_from_file_serve.mode == 'serve'


def test_extra_values_handling(config):
    """
    Tests that extra, undefined values can be added and accessed via
    dictionary-style access, but not attribute-style access.
    """
    config_dict = {
        'extra_root_key': 'top_level_value',
        'site': {
            'extra_site_key': 'site_value'
        }
    }
    config.update(config_dict)

    # Test dictionary-style access for extra keys (should work)
    assert config['extra_root_key'] == 'top_level_value'
    assert config.site['extra_site_key'] == 'site_value'

    # Test attribute-style access for extra keys (should raise AttributeError)
    with pytest.raises(AttributeError):
        _ = config.extra_root_key
    with pytest.raises(AttributeError):
        _ = config.site.extra_site_key

    # Test that defined keys are not stored in extras
    assert 'extra_root_key' in config.extras
    assert 'extra_site_key' in config.site.extras
    assert 'site_name' not in config.site.extras
    assert 'site_name' in config.site.__dict__


def test_key_error_for_undefined_key(config):
    """
    Tests that accessing a non-existent key using dictionary-style access
    raises a KeyError.
    """
    with pytest.raises(KeyError, match=r"undefined_key not found in Config."):
        _ = config['undefined_key']

    with pytest.raises(KeyError, match=r"undefined_key not found in SiteConfig."):
        _ = config.site['undefined_key']


def test_get_method_with_default_value(config):
    """
    Tests that the .get() method returns the default value for non-existent keys.
    """
    # Test top-level
    assert config.get('non_existent_key', 'default_root') == 'default_root'
    assert config.get('non_existent_key') is None  # Default None

    # Test nested within site
    assert config.site.get('non_existent_key_site', 'default_site') == 'default_site'
    assert config.site.get('non_existent_key_site') is None  # Default None

    # Test get for existing key returns its value
    assert config.site.get('site_name', 'default_name') == 'Site Title'


def test_base_config_setitem():
    """
    Tests that __setitem__ correctly updates both predefined attributes
    and the 'extras' dictionary.
    """
    site_config = SiteConfig()

    # 1. Update a predefined attribute
    site_config['site_name'] = 'New Name'
    assert site_config.site_name == 'New Name'
    assert site_config['site_name'] == 'New Name'
    assert 'site_name' not in site_config.extras  # Ensure predefined attributes are not stored in extras

    # 2. Add an extra, undefined attribute
    site_config['new_extra_key'] = 'extra_value'
    assert site_config.extras['new_extra_key'] == 'extra_value'
    assert site_config['new_extra_key'] == 'extra_value'
    # Verify that attribute-style access fails for extra keys
    with pytest.raises(AttributeError):
        _ = site_config.new_extra_key