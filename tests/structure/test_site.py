from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

import nkssg
from nkssg.structure.config import Config
from nkssg.structure.site import Site

@pytest.fixture
def base_config(tmp_path):
    (tmp_path / 'nkssg.yml').touch()
    
    config = Config.from_file(
        yaml_file_path=tmp_path / 'nkssg.yml',
        mode='build',
        base_dir=tmp_path
    )
    config.docs_dir.mkdir(exist_ok=True)
    return config

@patch('nkssg.structure.site.Plugins')
@patch('nkssg.structure.site.Themes')
@patch('nkssg.structure.site.Singles')
@patch('nkssg.structure.site.Archives')
def test_site_initialization(
    MockArchives, MockSingles, MockThemes, MockPlugins, base_config
):
    """Test that the Site class initializes its core components correctly."""
    mock_plugins_instance = MockPlugins.return_value
    mock_plugins_instance.do_action.side_effect = lambda action, target: target

    mock_themes_instance = MockThemes.return_value
    
    site = Site(base_config)

    MockPlugins.assert_called_once_with(base_config)
    MockThemes.assert_called_once_with(base_config)

    mock_plugins_instance.do_action.assert_any_call('after_load_plugins', target=base_config)
    mock_plugins_instance.do_action.assert_any_call('after_load_theme', target=mock_themes_instance)
    mock_plugins_instance.do_action.assert_any_call('after_setup_post_types', target=site.config)

    MockSingles.assert_called_once_with(site.config, mock_plugins_instance)
    MockArchives.assert_called_once_with(site.config, mock_plugins_instance)

    assert site.config is not None
    assert site.themes is not None
    assert site.singles is not None
    assert site.archives is not None


def test_setup_post_types_automatically_adds_from_dir(base_config):
    """Test that post types are automatically detected from the directory structure."""
    (base_config.docs_dir / 'post').mkdir()
    (base_config.docs_dir / 'page').mkdir()
    # This should be ignored as it's a file
    (base_config.docs_dir / 'notes.md').touch()

    site = Site(base_config)

    assert 'post' in site.config.post_type
    assert 'page' in site.config.post_type
    assert 'notes.md' not in site.config.post_type
    assert len(site.config.post_type) == 2 # Only 'post' and 'page'

def test_handle_missing_home_template(base_config, mocker):
    """Test that if home.html is missing, the first post_type is configured to act as the homepage."""
    (base_config.docs_dir / 'blog').mkdir()

    # Mock Themes to simulate missing home.html
    mocker.patch(
        'nkssg.structure.site.Themes.lookup_template',
        return_value=None
    )

    site = Site(base_config)
    blog_post_type = site.config.post_type['blog']

    assert blog_post_type.add_prefix_to_url is False
    assert blog_post_type.archive_type == 'section'
