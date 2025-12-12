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


def test_site_update_renders_html(site_fixture):
    """
    Integration test to verify that Site.update() correctly renders
    HTML content for a Single page using the configured theme.
    """
    config = site_fixture # site_fixture yields a Config object
    
    # Ensure all necessary directories exist for Config to resolve paths
    config.base_dir.mkdir(parents=True, exist_ok=True)
    config.docs_dir.mkdir(parents=True, exist_ok=True)
    config.themes_dir.mkdir(parents=True, exist_ok=True)
    (config.themes_dir / 'default').mkdir(parents=True, exist_ok=True)
    
    site = Site(config)
    
    # Perform setup and update operations
    site.setup()
    site.update()

    # Assertions
    assert len(site.singles.pages) == 1
    single_page = site.singles.pages[0]

    assert single_page.title == "My Test Post Title"
    assert single_page.content == "<p>This is the <strong>content</strong> of my test post.</p>"
    assert single_page.html is not None
    assert "My Test Post Title" in single_page.html
    assert "<h1>My Test Post Title</h1>" in single_page.html
    assert "This is the <strong>content</strong> of my test post." in single_page.html
    assert "<!DOCTYPE html>" in single_page.html
    assert "<html>" in single_page.html
    assert "<head>" in single_page.html
    assert "<body>" in single_page.html
    assert "</div>" in single_page.html
    assert "</html>" in single_page.html


def test_site_output_writes_files(site_fixture):
    """
    Integration test to verify that Site.output() correctly writes
    rendered HTML files to the public directory.
    """
    config = site_fixture  # site_fixture yields a Config object

    # Ensure all necessary directories exist for Config to resolve paths
    config.base_dir.mkdir(parents=True, exist_ok=True)
    config.docs_dir.mkdir(parents=True, exist_ok=True)
    config.themes_dir.mkdir(parents=True, exist_ok=True)
    (config.themes_dir / 'default').mkdir(parents=True, exist_ok=True)

    site = Site(config)

    # Perform setup, update, and output operations
    site.setup()
    site.update()
    site.output()

    # Assertions
    public_dir = config.public_dir
    assert public_dir.is_dir()

    # Check for the generated post HTML file
    expected_post_path = public_dir / "my-test-post-title" / "index.html"
    assert expected_post_path.is_file()

    # Verify content of the generated file
    generated_content = expected_post_path.read_text(encoding="utf-8")
    assert "<h1>My Test Post Title</h1>" in generated_content
    assert "This is the <strong>content</strong> of my test post." in generated_content
    assert "<!DOCTYPE html>" in generated_content
    assert "</html>" in generated_content

    # Check for static files (e.g., style.css if it existed in the theme)
    # For this fixture, we only added single.html, so there are no static files
    # to check, but this section shows where such checks would go.
    # For example:
    # expected_css_path = public_dir / "themes" / "default" / "style.css"
    # assert not expected_css_path.is_file() # Should not exist with current fixture setup


def test_copy_static_files(base_config, mocker):
    """Test that static files are copied correctly based on include/exclude rules."""
    config = base_config
    
    # --- Setup ---
    # Create static and theme directories
    static_dir = config.base_dir / "static"
    static_dir.mkdir()
    (static_dir / "image.jpg").touch()

    themes_dir = config.themes_dir
    theme_path = themes_dir / "mytheme"
    theme_path.mkdir(parents=True)
    (theme_path / "style.css").touch()
    (theme_path / "script.js").touch()
    (theme_path / "ignored.txt").touch()
    (theme_path / "template.html").touch() # Should not be copied by default

    config.static_dir = static_dir
    
    # Mock Themes object and its configuration
    mock_themes = MagicMock()
    mock_themes.dirs = [theme_path]
    mock_themes.cnf = {
        'static_include': ['*style.css', '*script.js'],
        'static_exclude': ['*.txt']
    }
    
    mocker.patch('nkssg.structure.site.Themes', return_value=mock_themes)
    
    site = Site(config)
    site.themes = mock_themes # Inject the mock
    
    # --- Execute ---
    site.copy_static_files()
    
    # --- Assert ---
    public_dir = config.public_dir
    
    # Check that regular static file was copied
    assert (public_dir / "image.jpg").is_file()
    
    # Check theme files based on rules
    theme_public_dir = public_dir / "themes" / "mytheme"
    assert (theme_public_dir / "style.css").is_file()
    assert (theme_public_dir / "script.js").is_file()
    
    # Check that excluded and non-included files were NOT copied
    assert not (theme_public_dir / "ignored.txt").exists()
    assert not (theme_public_dir / "template.html").exists()


def test_copy_static_files_skips_newer_files(base_config, mocker):
    """Test that copy_static_files does not overwrite newer files."""
    config = base_config
    
    static_dir = config.base_dir / "static"
    static_dir.mkdir()
    source_file = static_dir / "file.txt"
    source_file.touch()
    
    public_dir = config.public_dir
    public_dir.mkdir()
    dest_file = public_dir / "file.txt"
    dest_file.touch()
    
    # Make source older than destination
    source_mtime = source_file.stat().st_mtime
    import time
    time.sleep(0.01) # Ensure destination is newer
    dest_file.touch()
    dest_mtime_before = dest_file.stat().st_mtime
    
    assert source_mtime < dest_mtime_before

    config.static_dir = static_dir
    
    site = Site(config)
    
    site.copy_static_files()
    
    dest_mtime_after = dest_file.stat().st_mtime
    assert dest_mtime_after == dest_mtime_before # Timestamp should not have changed


def test_site_initialization_with_empty_docs_dir(base_config):
    """
    Test that Site initialization does not fail with StopIteration
    if the docs directory is empty and no post types are defined.
    """
    # Ensure docs dir is empty and has no subdirectories
    assert not any(base_config.docs_dir.iterdir())
    
    try:
        Site(base_config)
    except StopIteration:
        pytest.fail("Site initialization failed with StopIteration on empty docs dir.")

