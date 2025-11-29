import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from ruamel.yaml import YAML
import shutil

import nkssg  # Needed for default theme path
from nkssg.structure.config import Config
from nkssg.structure.themes import Themes


@pytest.fixture
def base_config(tmp_path):
    """Fixture to create a mock Config object with necessary Path attributes."""
    config = MagicMock(spec=Config)
    config.base_dir = tmp_path
    config.themes_dir = tmp_path / "themes"
    config.themes_dir.mkdir(exist_ok=True)
    config.theme = {}

    return config


@pytest.fixture
def create_theme_structure(tmp_path):
    """Helper to create theme directories and config files."""
    def _creator(theme_name, config_content=None, parent=None, templates=None):
        theme_dir = tmp_path / "themes" / theme_name
        theme_dir.mkdir(parents=True, exist_ok=True)

        if config_content:
            (theme_dir / f"{theme_name}.yml").write_text(config_content)

        if templates:
            for template_path, template_content in templates.items():
                file_path = theme_dir / template_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(template_content)
        return theme_dir
    return _creator


def test_init_no_themes_loads_default(base_config, create_theme_structure):
    """Test that if no themes are specified, the default theme is loaded."""
    # Ensure default theme exists for testing
    package_dir = Path(nkssg.__file__).parent
    default_theme_dir = package_dir / 'themes' / 'default'
    assert default_theme_dir.is_dir()

    themes = Themes(base_config)

    assert len(themes.dirs) == 1
    assert themes.dirs[0] == default_theme_dir
    assert 'default' in base_config.theme['name']
    assert base_config.theme['updated'] is True
    assert themes.cnf


def test_init_single_theme_loads_correctly(base_config, create_theme_structure):
    """Test loading a single theme specified in config."""
    theme_name = "my_single_theme"
    create_theme_structure(
        theme_name,
        config_content="key: value",
        templates={'index.html': 'content'}
    )
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    assert len(themes.dirs) == 1
    assert themes.dirs[0] == base_config.themes_dir / theme_name
    assert themes.cnf == {'key': 'value'}
    assert base_config.theme['updated'] is True


def test_init_child_theme_loads_correctly_with_parent_priority(
    base_config, create_theme_structure
):
    """Test loading a child theme which should prioritize its templates over parent."""
    parent_theme = "parent_theme"
    child_theme = "child_theme"

    create_theme_structure(
        parent_theme,
        config_content="parent_key: parent_value\ncommon_key: parent_common",
        templates={'index.html': 'parent_index', 'style.css': 'parent_style'}
    )
    create_theme_structure(
        child_theme,
        config_content="child_key: child_value\ncommon_key: child_common",
        templates={'index.html': 'child_index', 'script.js': 'child_script'}
    )

    base_config.theme['name'] = parent_theme
    base_config.theme['child'] = child_theme

    themes = Themes(base_config)

    assert len(themes.dirs) == 2
    # Child theme directory should come first for lookup priority
    assert themes.dirs[0] == base_config.themes_dir / child_theme
    assert themes.dirs[1] == base_config.themes_dir / parent_theme

    # Config should be merged, child overriding parent
    expected_config = {
        'parent_key': 'parent_value',
        'child_key': 'child_value',
        'common_key': 'child_common'
    }
    assert themes.cnf == expected_config
    assert base_config.theme['updated'] is True


def test_load_theme_non_existent_theme_is_ignored(
    base_config, caplog, create_theme_structure
):
    """Test that a non-existent theme is ignored and the default theme is used as a fallback."""
    base_config.theme['name'] = "non_existent_theme"

    themes = Themes(base_config)

    assert "non_existent_theme is not found" in caplog.text

    # Assert that it fell back to loading the default theme.
    assert len(themes.dirs) == 1
    package_dir = Path(nkssg.__file__).parent
    default_theme_dir = package_dir / 'themes' / 'default'
    assert themes.dirs[0] == default_theme_dir
    assert 'name' in base_config.theme
    assert base_config.theme['updated'] is True


def test_load_theme_config_invalid_yaml(base_config, caplog, create_theme_structure):
    """Test handling of invalid YAML in theme configuration."""
    theme_name = "bad_config_theme"
    create_theme_structure(theme_name, config_content="key: { value")
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    assert not themes.cnf
    assert "Failed to load config for bad_config_theme" in caplog.text


def test_lookup_template_exists_in_single_theme(base_config, create_theme_structure):
    """Test lookup when template exists in a single theme."""
    theme_name = "test_theme"
    create_theme_structure(
        theme_name, templates={'layout/header.html': 'header_content'}
    )
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    found_path = themes.lookup_template(['header.html', 'layout/header.html'])
    assert found_path == 'layout/header.html'

    found_path = themes.lookup_template(['non_existent.html', 'header.html'])
    assert found_path == 'layout/header.html'


def test_lookup_template_child_theme_priority(base_config, create_theme_structure):
    """Test lookup with child and parent themes, child should take precedence."""
    parent_theme = "parent_theme_lookup"
    child_theme = "child_theme_lookup"

    create_theme_structure(
        parent_theme,
        templates={'shared.html': 'parent_shared', 'specific_parent.html': 'content'}
    )
    create_theme_structure(
        child_theme,
        templates={'shared.html': 'child_shared', 'specific_child.html': 'content'}
    )

    base_config.theme['name'] = parent_theme
    base_config.theme['child'] = child_theme

    themes = Themes(base_config)

    found_path = themes.lookup_template(['shared.html'])
    # Should be from child due to priority
    assert found_path == 'shared.html'


def test_lookup_template_not_found(base_config, create_theme_structure):
    """Test lookup when template does not exist in any loaded theme."""
    theme_name = "empty_theme"
    create_theme_structure(theme_name)
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    found_path = themes.lookup_template(['non_existent_template.html'])
    assert found_path == ''


def test_lookup_template_full_path(base_config, create_theme_structure):
    """Test lookup when full_path is True."""
    theme_name = "full_path_theme"
    theme_dir = create_theme_structure(
        theme_name, templates={'pages/home.html': 'home_content'}
    )
    base_config.theme['name'] = theme_name

    themes = Themes(base_config)

    found_path = themes.lookup_template(['home.html'], full_path=True)
    expected_path = str(theme_dir / 'pages' / 'home.html').replace('\\', '/')
    assert found_path == expected_path
