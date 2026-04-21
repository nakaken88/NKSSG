import pytest

from pathlib import Path

from nkssg.structure.config import Config, SiteConfig


@pytest.fixture
def config():
    return Config()


# 1. Initialization & Defaults
def test_default_config(config):
    assert config['site']['site_name'] == 'Site Title'
    assert config.site.site_name == 'Site Title'
    assert config.site.site_url == ''
    assert config.plugins.get('select-pages') == {}

    assert 'md' in config.doc_ext

    assert config.taxonomy == {}
    assert config.use_abs_url is True


def test_config_init_with_base_dir(tmp_path):
    custom_base_dir = tmp_path / "custom_base"
    custom_base_dir.mkdir()

    config = Config(base_dir=custom_base_dir)

    assert config.base_dir == custom_base_dir
    assert config.docs_dir == custom_base_dir / 'docs'
    assert config.public_dir == custom_base_dir / 'public'
    assert config.static_dir == custom_base_dir / 'static'
    assert config.themes_dir == custom_base_dir / 'themes'


def test_mode_handling(tmp_path: Path):
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


# 2. Dictionary-like Behavior
def test_base_config_setitem():
    site_config = SiteConfig()

    site_config['site_name'] = 'New Name'
    assert site_config.site_name == 'New Name'
    assert site_config['site_name'] == 'New Name'
    assert 'site_name' not in site_config.extras

    site_config['new_extra_key'] = 'extra_value'
    assert site_config.extras['new_extra_key'] == 'extra_value'
    assert site_config['new_extra_key'] == 'extra_value'
    with pytest.raises(AttributeError):
        _ = site_config.new_extra_key


def test_extra_values_handling(config):
    config_dict = {
        'extra_root_key': 'top_level_value',
        'site': {
            'extra_site_key': 'site_value'
        }
    }
    config.update(config_dict)

    assert config['extra_root_key'] == 'top_level_value'
    assert config.site['extra_site_key'] == 'site_value'

    with pytest.raises(AttributeError):
        _ = config.extra_root_key
    with pytest.raises(AttributeError):
        _ = config.site.extra_site_key

    assert 'extra_root_key' in config.extras
    assert 'extra_site_key' in config.site.extras
    assert 'site_name' not in config.site.extras
    assert 'site_name' in config.site.__dict__


def test_key_error_for_undefined_key(config):
    with pytest.raises(KeyError, match=r"undefined_key not found in Config."):
        _ = config['undefined_key']

    with pytest.raises(KeyError, match=r"undefined_key not found in SiteConfig."):
        _ = config.site['undefined_key']


def test_get_method_with_default_value(config):
    assert config.get('non_existent_key', 'default_root') == 'default_root'
    assert config.get('non_existent_key') is None

    assert config.site.get('non_existent_key_site', 'default_site') == 'default_site'
    assert config.site.get('non_existent_key_site') is None

    assert config.site.get('site_name', 'default_name') == 'Site Title'


# 3. update method
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
    assert config.site.site_url == 'http://example.com'  # trailing slash is removed
    assert config.site.site_url_original == 'http://example.com/'
    assert config.site.site_image == '/images/hero.jpg'  # becomes a relative path


def test_post_type_config(config):
    config_dict = {
        'post_type': {
            'post': {
                'permalink': '/%Y/%m/%d/',
                'archive_type': 'Date',  # uppercase
            },
            'sample': {
                'archive_type': 'none',
            },
            'page': {
                'archive_type': 'invalid_type',  # falls back to 'section'
            },
            'blog': {
                'archive_type': 'Simple',  # uppercase
            },
            'news': {
                'archive_type': 'date',
            }
        },
    }

    config.update(config_dict)

    assert config.post_type['post'].permalink == '/%Y/%m/%d/'
    assert config.post_type['post'].archive_type == 'date'
    assert config.post_type['sample'].archive_type == 'none'
    assert config.post_type['sample'].permalink == '/{slug}/'
    assert config.post_type['page'].archive_type == 'section'
    assert config.post_type['blog'].archive_type == 'simple'
    assert config.post_type['news'].archive_type == 'date'


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


# 4. from_file
def test_from_file_success(tmp_path: Path):
    config_content = """
    site:
      site_name: 'Test Site'
    """
    config_file = tmp_path / "test.yml"
    config_file.write_text(config_content, encoding="utf-8")

    config = Config.from_file(yaml_file_path=config_file)

    assert config.site.site_name == 'Test Site'


def test_from_file_with_base_dir(tmp_path: Path):
    config_content = """
    site:
      site_name: 'Test Site with Custom Base'
    """
    config_file = tmp_path / "test.yml"
    config_file.write_text(config_content, encoding="utf-8")

    custom_base_dir = tmp_path / "custom_root"
    custom_base_dir.mkdir()

    config = Config.from_file(yaml_file_path=config_file, base_dir=custom_base_dir)

    assert config.base_dir == custom_base_dir
    assert config.site.site_name == 'Test Site with Custom Base'
    assert config.docs_dir == custom_base_dir / 'docs'
    assert config.public_dir == custom_base_dir / 'public'
    assert config.static_dir == custom_base_dir / 'static'
    assert config.themes_dir == custom_base_dir / 'themes'


def test_from_file_ignores_mode_key(tmp_path: Path):
    """mode in YAML is ignored so the CLI-specified mode takes precedence."""
    config_content = """
    mode: serve
    site:
      site_name: 'Test Site from YAML'
    """
    config_file = tmp_path / "test_with_mode.yml"
    config_file.write_text(config_content, encoding="utf-8")

    config = Config.from_file(yaml_file_path=config_file, mode='build')

    assert config.mode == 'build'
    assert config.site.site_name == 'Test Site from YAML'


def test_from_file_not_found():
    with pytest.raises(FileNotFoundError):
        Config.from_file(yaml_file_path=Path("non_existent_file.yml"))


def test_from_file_with_invalid_yaml(tmp_path: Path):
    config_content = "site: { site_name: 'Test Site }"
    config_file = tmp_path / "test.yml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(ValueError, match="The YAML format is incorrect: .*"):
        Config.from_file(yaml_file_path=config_file)


def test_from_file_with_empty_yaml(tmp_path: Path):
    config_file = tmp_path / "empty.yml"
    config_file.touch()

    config = Config.from_file(yaml_file_path=config_file)
    assert config.site.site_name == 'Site Title'
    assert config.use_abs_url is True


def test_term_missing_name_key_raises_error(tmp_path: Path):
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


# 5. Taxonomy Parsing
def test_invalid_term_name_is_ignored(tmp_path: Path):
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
              - name: cat21  # duplicate: overwrites slug only
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
